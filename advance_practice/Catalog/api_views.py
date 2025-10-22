from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from .models import Category, Product, ProductImage, Comment, Voucher
from .serializers import (
    CategorySerializer, CategoryTreeSerializer,
    ProductListSerializer, ProductDetailSerializer,
    ProductImageSerializer, CommentSerializer, VoucherSerializer
)


@extend_schema_view(
    list=extend_schema(
        tags=['Categories'],
        summary='List Categories',
        description='Get paginated list of categories with optional filtering',
        parameters=[
            OpenApiParameter(
                name='parent',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by parent category ID (use 0 or null for root categories)',
                required=False
            ),
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Search in category name and description',
                required=False
            )
        ]
    ),
    create=extend_schema(
        tags=['Categories'],
        summary='Create Category',
        description='Create a new category (with optional image upload)'
    ),
    retrieve=extend_schema(
        tags=['Categories'],
        summary='Get Category',
        description='Get details of a specific category'
    ),
    update=extend_schema(
        tags=['Categories'],
        summary='Update Category',
        description='Update category details'
    ),
    partial_update=extend_schema(
        tags=['Categories'],
        summary='Partial Update Category',
        description='Partially update category details'
    ),
    destroy=extend_schema(
        tags=['Categories'],
        summary='Delete Category',
        description='Delete a category'
    )
)
class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Category CRUD operations with tree structure support
    
    Endpoints:
    - GET /api/categories/ - List all categories with pagination
    - POST /api/categories/ - Create new category (with image upload)
    - GET /api/categories/{id}/ - Get single category
    - PUT/PATCH /api/categories/{id}/ - Update category
    - DELETE /api/categories/{id}/ - Delete category
    - GET /api/categories/tree/ - Get categories in tree structure
    - GET /api/categories/root/ - Get only root categories (no parent)
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        """Filter categories based on query params"""
        queryset = Category.objects.all()
        
        # Filter by parent
        parent_id = self.request.query_params.get('parent', None)
        if parent_id is not None:
            if parent_id == '0' or parent_id.lower() == 'null':
                queryset = queryset.filter(parent__isnull=True)
            else:
                queryset = queryset.filter(parent_id=parent_id)
        
        return queryset
    
    @extend_schema(
        tags=['Categories'],
        summary='Get Category Tree',
        description='Get all categories in a hierarchical tree structure',
        responses={200: CategoryTreeSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def tree(self, request):
        """
        Get categories in tree structure (nested)
        GET /api/categories/tree/
        """
        root_categories = Category.objects.filter(parent__isnull=True)
        serializer = CategoryTreeSerializer(root_categories, many=True, context={'request': request})
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Categories'],
        summary='Get Root Categories',
        description='Get only root categories (categories without parent)',
        responses={200: CategorySerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def root(self, request):
        """
        Get only root categories (categories without parent)
        GET /api/categories/root/
        """
        root_categories = Category.objects.filter(parent__isnull=True)
        serializer = self.get_serializer(root_categories, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Categories'],
        summary='Get Category Children',
        description='Get all child categories of a specific category',
        responses={200: CategorySerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def children(self, request, pk=None):
        """
        Get all children of a specific category
        GET /api/categories/{id}/children/
        """
        category = self.get_object()
        children = category.children.all()
        serializer = self.get_serializer(children, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Categories'],
        summary='Get Category Products',
        description='Get all products in a specific category',
        responses={200: ProductListSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        """
        Get all products in a specific category
        GET /api/categories/{id}/products/
        """
        category = self.get_object()
        products = category.products.all()
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        tags=['Products'],
        summary='List Products',
        description='Get paginated list of products with filtering and search',
        parameters=[
            OpenApiParameter(
                name='categories',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by category ID',
                required=False
            ),
            OpenApiParameter(
                name='min_price',
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                description='Minimum price',
                required=False
            ),
            OpenApiParameter(
                name='max_price',
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                description='Maximum price',
                required=False
            ),
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Search in product name and description',
                required=False
            ),
            OpenApiParameter(
                name='ordering',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Order by: name, price, created_at, view_count (prefix with - for descending)',
                required=False
            )
        ]
    ),
    create=extend_schema(
        tags=['Products'],
        summary='Create Product',
        description='Create a new product with optional thumbnail and images'
    ),
    retrieve=extend_schema(
        tags=['Products'],
        summary='Get Product',
        description='Get product details (increments view count)'
    ),
    update=extend_schema(
        tags=['Products'],
        summary='Update Product',
        description='Update product details'
    ),
    partial_update=extend_schema(
        tags=['Products'],
        summary='Partial Update Product',
        description='Partially update product details'
    ),
    destroy=extend_schema(
        tags=['Products'],
        summary='Delete Product',
        description='Delete a product'
    )
)
class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Product CRUD operations
    
    Endpoints:
    - GET /api/products/ - List all products with pagination
    - POST /api/products/ - Create new product (with images upload)
    - GET /api/products/{id}/ - Get single product
    - PUT/PATCH /api/products/{id}/ - Update product
    - DELETE /api/products/{id}/ - Delete product
    - POST /api/products/{id}/upload_images/ - Upload additional images
    - DELETE /api/products/{id}/delete_image/ - Delete a specific image
    - POST /api/products/{id}/update_thumbnail/ - Update product thumbnail
    """
    queryset = Product.objects.all()
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['categories', 'voucher_enabled']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'price', 'created_at', 'view_count']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Use different serializers for list and detail views"""
        if self.action == 'list':
            return ProductListSerializer
        return ProductDetailSerializer
    
    def get_queryset(self):
        """Filter products based on query params"""
        queryset = Product.objects.prefetch_related('categories', 'images').all()
        
        # Filter by price range
        min_price = self.request.query_params.get('min_price', None)
        max_price = self.request.query_params.get('max_price', None)
        
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        
        # Filter by category (including subcategories)
        category_id = self.request.query_params.get('category', None)
        if category_id:
            queryset = queryset.filter(categories__id=category_id)
        
        return queryset.distinct()
    
    def retrieve(self, request, *args, **kwargs):
        """Increment view count when retrieving a product"""
        instance = self.get_object()
        instance.view_count += 1
        instance.save(update_fields=['view_count'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Products'],
        summary='Upload Product Images',
        description='Upload multiple images to a product',
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'images': {
                        'type': 'array',
                        'items': {'type': 'string', 'format': 'binary'}
                    },
                    'caption': {'type': 'string'}
                }
            }
        },
        responses={
            201: ProductImageSerializer(many=True),
            400: {'description': 'No images provided'}
        }
    )
    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_images(self, request, pk=None):
        """
        Upload additional images to a product
        POST /api/products/{id}/upload_images/
        Body: images[] (multiple files)
        """
        product = self.get_object()
        images = request.FILES.getlist('images')
        
        if not images:
            return Response(
                {'error': 'No images provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_images = []
        for image in images:
            product_image = ProductImage.objects.create(
                product=product,
                image=image,
                caption=request.data.get('caption', '')
            )
            created_images.append(product_image)
        
        serializer = ProductImageSerializer(created_images, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @extend_schema(
        tags=['Products'],
        summary='Delete Product Image',
        description='Delete a specific product image',
        parameters=[
            OpenApiParameter(
                name='image_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='ID of the image to delete',
                required=True
            )
        ],
        responses={
            204: {'description': 'Image deleted successfully'},
            400: {'description': 'image_id parameter required'},
            404: {'description': 'Image not found'}
        }
    )
    @action(detail=True, methods=['delete'])
    def delete_image(self, request, pk=None):
        """
        Delete a specific product image
        DELETE /api/products/{id}/delete_image/?image_id={image_id}
        """
        product = self.get_object()
        image_id = request.query_params.get('image_id')
        
        if not image_id:
            return Response(
                {'error': 'image_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            image = ProductImage.objects.get(id=image_id, product=product)
            image.delete()
            return Response(
                {'message': 'Image deleted successfully'},
                status=status.HTTP_204_NO_CONTENT
            )
        except ProductImage.DoesNotExist:
            return Response(
                {'error': 'Image not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @extend_schema(
        tags=['Products'],
        summary='Update Product Thumbnail',
        description='Update or replace product thumbnail image',
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'thumbnail': {'type': 'string', 'format': 'binary'}
                },
                'required': ['thumbnail']
            }
        },
        responses={
            200: ProductDetailSerializer,
            400: {'description': 'No thumbnail provided'}
        }
    )
    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def update_thumbnail(self, request, pk=None):
        """
        Update product thumbnail
        POST /api/products/{id}/update_thumbnail/
        Body: thumbnail (image file)
        """
        product = self.get_object()
        thumbnail = request.FILES.get('thumbnail')
        
        if not thumbnail:
            return Response(
                {'error': 'No thumbnail provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Delete old thumbnail if exists
        if product.thumbnail:
            product.thumbnail.delete()
        
        product.thumbnail = thumbnail
        product.save()
        
        serializer = self.get_serializer(product)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Products'],
        summary='Get Most Viewed Products',
        description='Get list of most viewed products',
        parameters=[
            OpenApiParameter(
                name='limit',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Number of products to return (default: 10)',
                required=False
            )
        ],
        responses={200: ProductListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def most_viewed(self, request):
        """
        Get most viewed products
        GET /api/products/most_viewed/?limit=10
        """
        limit = int(request.query_params.get('limit', 10))
        products = Product.objects.order_by('-view_count')[:limit]
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Products'],
        summary='Get Latest Products',
        description='Get list of latest products',
        parameters=[
            OpenApiParameter(
                name='limit',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Number of products to return (default: 10)',
                required=False
            )
        ],
        responses={200: ProductListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def latest(self, request):
        """
        Get latest products
        GET /api/products/latest/?limit=10
        """
        limit = int(request.query_params.get('limit', 10))
        products = Product.objects.order_by('-created_at')[:limit]
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        tags=['Product Images'],
        summary='List Product Images',
        description='Get list of all product images'
    ),
    create=extend_schema(
        tags=['Product Images'],
        summary='Create Product Image',
        description='Upload a new product image'
    ),
    retrieve=extend_schema(
        tags=['Product Images'],
        summary='Get Product Image',
        description='Get details of a specific product image'
    ),
    update=extend_schema(
        tags=['Product Images'],
        summary='Update Product Image',
        description='Update product image details'
    ),
    partial_update=extend_schema(
        tags=['Product Images'],
        summary='Partial Update Product Image',
        description='Partially update product image details'
    ),
    destroy=extend_schema(
        tags=['Product Images'],
        summary='Delete Product Image',
        description='Delete a product image'
    )
)
class ProductImageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing product images independently
    
    Endpoints:
    - GET /api/product-images/ - List all product images
    - POST /api/product-images/ - Create new product image
    - GET /api/product-images/{id}/ - Get single image
    - PUT/PATCH /api/product-images/{id}/ - Update image
    - DELETE /api/product-images/{id}/ - Delete image
    """
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['product']


@extend_schema_view(
    list=extend_schema(
        tags=['Comments'],
        summary='List Comments',
        description='Get list of product comments with filtering'
    ),
    create=extend_schema(
        tags=['Comments'],
        summary='Create Comment',
        description='Create a new comment on a product (authenticated users only)'
    ),
    retrieve=extend_schema(
        tags=['Comments'],
        summary='Get Comment',
        description='Get details of a specific comment'
    ),
    update=extend_schema(
        tags=['Comments'],
        summary='Update Comment',
        description='Update comment (owner only)'
    ),
    partial_update=extend_schema(
        tags=['Comments'],
        summary='Partial Update Comment',
        description='Partially update comment (owner only)'
    ),
    destroy=extend_schema(
        tags=['Comments'],
        summary='Delete Comment',
        description='Delete comment (owner only)'
    )
)
class CommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for product comments
    
    Endpoints:
    - GET /api/comments/ - List all comments
    - POST /api/comments/ - Create new comment (authenticated)
    - GET /api/comments/{id}/ - Get single comment
    - PUT/PATCH /api/comments/{id}/ - Update comment (owner only)
    - DELETE /api/comments/{id}/ - Delete comment (owner only)
    """
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['product', 'user']
    ordering_fields = ['created_at']
    ordering = ['created_at']
    
    def perform_create(self, serializer):
        """Set user to current authenticated user"""
        serializer.save(user=self.request.user)
    
    def perform_update(self, serializer):
        """Only allow owner to update"""
        if serializer.instance.user != self.request.user:
            raise PermissionError("You can only edit your own comments")
        serializer.save()
    
    def perform_destroy(self, instance):
        """Only allow owner to delete"""
        if instance.user != self.request.user:
            raise PermissionError("You can only delete your own comments")
        instance.delete()


@extend_schema_view(
    list=extend_schema(
        tags=['Vouchers'],
        summary='List User Vouchers',
        description='Get list of vouchers belonging to the current user'
    ),
    retrieve=extend_schema(
        tags=['Vouchers'],
        summary='Get Voucher',
        description='Get details of a specific voucher'
    )
)
class VoucherViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing vouchers (read-only)
    
    Endpoints:
    - GET /api/vouchers/ - List user's vouchers
    - GET /api/vouchers/{id}/ - Get single voucher
    """
    queryset = Voucher.objects.all()
    serializer_class = VoucherSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['product']
    
    def get_queryset(self):
        """Only show vouchers belonging to current user"""
        return Voucher.objects.filter(user=self.request.user)


# ==================== REPORT APIs ====================

@extend_schema(
    tags=['Reports'],
    summary='Report Endpoints Overview',
    description='Get list of available report endpoints',
    responses={
        200: {
            'description': 'List of report endpoints',
            'examples': {
                'application/json': {
                    'message': 'Available report endpoints',
                    'endpoints': {
                        'products_per_category': '/api/reports/products-per-category/',
                        'product_views': '/api/reports/product-views/{product_id}/',
                        'product_comments': '/api/reports/product-comments/{product_id}/',
                        'category_stats': '/api/reports/category-stats/'
                    }
                }
            }
        }
    }
)
class ReportAPIView(APIView):
    """
    API endpoint for various reports
    
    Endpoints:
    - GET /api/reports/products-per-category/ - Total products per category
    - GET /api/reports/product-views/{id}/ - Total views of a specific product
    - GET /api/reports/product-comments/{id}/ - Total comments on a specific product
    - GET /api/reports/category-stats/ - Detailed statistics for all categories
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Return available report endpoints"""
        return Response({
            'message': 'Available report endpoints',
            'endpoints': {
                'products_per_category': '/api/reports/products-per-category/',
                'product_views': '/api/reports/product-views/{product_id}/',
                'product_comments': '/api/reports/product-comments/{product_id}/',
                'category_stats': '/api/reports/category-stats/',
            }
        })


@extend_schema(
    tags=['Reports'],
    summary='Products Per Category Report',
    description='Get total number of products in each category',
    responses={
        200: {
            'description': 'Products per category statistics',
            'examples': {
                'application/json': {
                    'total_categories': 5,
                    'categories': [
                        {
                            'id': 1,
                            'name': 'Electronics',
                            'slug': 'electronics',
                            'product_count': 15
                        }
                    ]
                }
            }
        }
    }
)
class ProductsPerCategoryReportAPIView(APIView):
    """
    Report: Total of products per category
    GET /api/reports/products-per-category/
    
    Returns count of products in each category
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Annotate categories with product count
        categories = Category.objects.annotate(
            product_count=Count('products')
        ).values('id', 'name', 'slug', 'product_count').order_by('-product_count')
        
        return Response({
            'total_categories': categories.count(),
            'categories': list(categories)
        })


@extend_schema(
    tags=['Reports'],
    summary='Product Views Report',
    description='Get total view count for a specific product',
    parameters=[
        OpenApiParameter(
            name='product_id',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description='Product ID',
            required=True
        )
    ],
    responses={
        200: {
            'description': 'Product view statistics',
            'examples': {
                'application/json': {
                    'product_id': 1,
                    'product_name': 'iPhone 15',
                    'product_slug': 'iphone-15',
                    'total_views': 150,
                    'created_at': '2025-01-01T00:00:00Z'
                }
            }
        },
        404: {'description': 'Product not found'}
    }
)
class ProductViewsReportAPIView(APIView):
    """
    Report: Total views of a product
    GET /api/reports/product-views/{product_id}/
    
    Returns view count for a specific product
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
            return Response({
                'product_id': product.id,
                'product_name': product.name,
                'product_slug': product.slug,
                'total_views': product.view_count,
                'created_at': product.created_at,
            })
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )


@extend_schema(
    tags=['Reports'],
    summary='Product Comments Report',
    description='Get total comments and comment list for a specific product',
    parameters=[
        OpenApiParameter(
            name='product_id',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description='Product ID',
            required=True
        )
    ],
    responses={
        200: {
            'description': 'Product comments statistics',
            'examples': {
                'application/json': {
                    'product_id': 1,
                    'product_name': 'iPhone 15',
                    'product_slug': 'iphone-15',
                    'total_comments': 25,
                    'comments': [
                        {
                            'id': 1,
                            'body': 'Great product!',
                            'created_at': '2025-01-01T00:00:00Z',
                            'user__username': 'john',
                            'user__email': 'john@example.com'
                        }
                    ]
                }
            }
        },
        404: {'description': 'Product not found'}
    }
)
class ProductCommentsReportAPIView(APIView):
    """
    Report: Total comments on a product
    GET /api/reports/product-comments/{product_id}/
    
    Returns comment count and list of comments for a specific product
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
            comments = product.comments.all()
            total_comments = comments.count()
            
            # Get comment details with user info
            comment_list = comments.values(
                'id', 'body', 'created_at', 'user__username', 'user__email'
            ).order_by('-created_at')
            
            return Response({
                'product_id': product.id,
                'product_name': product.name,
                'product_slug': product.slug,
                'total_comments': total_comments,
                'comments': list(comment_list)
            })
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )


@extend_schema(
    tags=['Reports'],
    summary='Category Statistics Report',
    description='Get comprehensive statistics for all categories including product count, views, and comments',
    responses={
        200: {
            'description': 'Detailed category statistics',
            'examples': {
                'application/json': {
                    'total_categories': 5,
                    'statistics': [
                        {
                            'category_id': 1,
                            'category_name': 'Electronics',
                            'category_slug': 'electronics',
                            'total_products': 15,
                            'total_views': 500,
                            'total_comments': 75,
                            'has_parent': False,
                            'parent_name': None
                        }
                    ]
                }
            }
        }
    }
)
class CategoryStatsReportAPIView(APIView):
    """
    Report: Detailed statistics for all categories
    GET /api/reports/category-stats/
    
    Returns comprehensive statistics including product count, total views, comments
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        categories = Category.objects.all()
        stats = []
        
        for category in categories:
            products = category.products.all()
            total_views = sum(p.view_count for p in products)
            total_comments = Comment.objects.filter(product__in=products).count()
            
            stats.append({
                'category_id': category.id,
                'category_name': category.name,
                'category_slug': category.slug,
                'total_products': products.count(),
                'total_views': total_views,
                'total_comments': total_comments,
                'has_parent': category.parent is not None,
                'parent_name': category.parent.name if category.parent else None,
            })
        
        # Sort by total products descending
        stats.sort(key=lambda x: x['total_products'], reverse=True)
        
        return Response({
            'total_categories': len(stats),
            'statistics': stats
        })
