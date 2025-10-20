from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from .models import Category, Product, ProductImage, Comment, Voucher
from .serializers import (
    CategorySerializer, CategoryTreeSerializer,
    ProductListSerializer, ProductDetailSerializer,
    ProductImageSerializer, CommentSerializer, VoucherSerializer
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
    permission_classes = [IsAuthenticatedOrReadOnly]
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
    
    @action(detail=False, methods=['get'])
    def tree(self, request):
        """
        Get categories in tree structure (nested)
        GET /api/categories/tree/
        """
        root_categories = Category.objects.filter(parent__isnull=True)
        serializer = CategoryTreeSerializer(root_categories, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def root(self, request):
        """
        Get only root categories (categories without parent)
        GET /api/categories/root/
        """
        root_categories = Category.objects.filter(parent__isnull=True)
        serializer = self.get_serializer(root_categories, many=True)
        return Response(serializer.data)
    
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
    permission_classes = [IsAuthenticatedOrReadOnly]
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
    permission_classes = [IsAuthenticatedOrReadOnly]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['product']


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
    permission_classes = [IsAuthenticatedOrReadOnly]
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
