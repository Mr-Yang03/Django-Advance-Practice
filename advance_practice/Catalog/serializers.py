from rest_framework import serializers
from .models import Category, Product, ProductImage, Comment, Voucher
from django.utils.text import slugify
from PIL import Image
import io
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys


class CategoryTreeSerializer(serializers.ModelSerializer):
    """Serializer for Category with children (tree structure)"""
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'image', 'parent', 'children', 'created_at', 'updated_at']
        read_only_fields = ['slug', 'created_at', 'updated_at']
    
    def get_children(self, obj):
        """Get all child categories"""
        children = obj.children.all()
        if children:
            return CategoryTreeSerializer(children, many=True).data
        return []


class CategorySerializer(serializers.ModelSerializer):
    """Basic Category serializer for CRUD operations"""
    children_count = serializers.SerializerMethodField()
    products_count = serializers.SerializerMethodField()
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description', 'image', 
            'parent', 'parent_name', 'children_count', 'products_count',
            'editing_user', 'edit_lock_time',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['slug', 'editing_user', 'edit_lock_time', 'created_at', 'updated_at']
    
    def get_children_count(self, obj):
        """Count of child categories"""
        return obj.children.count()
    
    def get_products_count(self, obj):
        """Count of products in this category"""
        return obj.products.count()
    
    def validate_parent(self, value):
        """Prevent circular references in category tree"""
        if value and self.instance:
            # Check if trying to set parent to self
            if value.id == self.instance.id:
                raise serializers.ValidationError("A category cannot be its own parent.")
            
            # Check if trying to set parent to one of its descendants
            current = value
            while current.parent:
                if current.parent.id == self.instance.id:
                    raise serializers.ValidationError(
                        "Cannot set parent to a descendant category."
                    )
                current = current.parent
        return value
    
    def create(self, validated_data):
        """Auto-generate slug from name"""
        if 'slug' not in validated_data or not validated_data['slug']:
            validated_data['slug'] = slugify(validated_data['name'])
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Update slug if name changes"""
        if 'name' in validated_data and validated_data['name'] != instance.name:
            validated_data['slug'] = slugify(validated_data['name'])
        return super().update(instance, validated_data)


class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer for Product Images"""
    
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'caption', 'created_at']
        read_only_fields = ['created_at']


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for product list"""
    categories = CategorySerializer(many=True, read_only=True)
    thumbnail_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'price', 'thumbnail', 'thumbnail_url',
            'categories', 'view_count', 'created_at'
        ]
        read_only_fields = ['slug', 'view_count', 'created_at']
    
    def get_thumbnail_url(self, obj):
        """Get full URL for thumbnail"""
        if obj.thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.thumbnail.url)
        return None


class ProductDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single product"""
    images = ProductImageSerializer(many=True, read_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        help_text="Upload multiple images for the product"
    )
    
    # Read: Show category details
    categories = CategorySerializer(many=True, read_only=True)
    
    # Write: Select categories by ID (supports multiple selection)
    category_ids = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        many=True,
        write_only=True,
        required=False,
        help_text="Select one or more categories for this product",
        style={'base_template': 'select_multiple.html'}
    )
    
    thumbnail_url = serializers.SerializerMethodField()
    available_vouchers = serializers.SerializerMethodField()
    user_has_claimed = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'price', 
            'thumbnail', 'thumbnail_url', 'view_count',
            'categories', 'category_ids', 'images', 'uploaded_images',
            'voucher_enabled', 'voucher_quantity', 'available_vouchers', 'user_has_claimed',
            'editing_user', 'edit_lock_time',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['slug', 'view_count', 'editing_user', 'edit_lock_time', 'created_at', 'updated_at']
        extra_kwargs = {
            'name': {'help_text': 'Product name'},
            'description': {'help_text': 'Detailed product description'},
            'price': {'help_text': 'Product price in VND'},
            'thumbnail': {'help_text': 'Main product image (optional - auto-generated from first uploaded image if not provided)'},
        }
    
    def get_thumbnail_url(self, obj):
        """Get full URL for thumbnail"""
        if obj.thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.thumbnail.url)
        return None
    
    def get_available_vouchers(self, obj):
        """
        Always return actual voucher quantity remaining.
        """
        return obj.voucher_quantity if obj.voucher_enabled else 0
    
    def get_user_has_claimed(self, obj):
        """
        Check if current user has already claimed voucher for this product.
        Returns True if user has voucher, False otherwise.
        """
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        
        # Check if user already has a voucher for this product
        return Voucher.objects.filter(product=obj, user=request.user).exists()
    
    def create_thumbnail(self, image):
        """Create thumbnail from uploaded image"""
        img = Image.open(image)
        
        # Convert to RGB if necessary
        if img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGB')
        
        # Create thumbnail (300x300)
        img.thumbnail((300, 300), Image.Resampling.LANCZOS)
        
        # Save to BytesIO
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=85)
        output.seek(0)
        
        # Create InMemoryUploadedFile
        return InMemoryUploadedFile(
            output, 'ImageField',
            f"thumb_{image.name}",
            'image/jpeg',
            sys.getsizeof(output), None
        )
    
    def create(self, validated_data):
        """Create product with images and thumbnail"""
        uploaded_images = validated_data.pop('uploaded_images', [])
        category_ids = validated_data.pop('category_ids', [])
        
        # Auto-generate slug
        if 'slug' not in validated_data or not validated_data['slug']:
            validated_data['slug'] = slugify(validated_data['name'])
        
        # Create thumbnail from first uploaded image if no thumbnail provided
        if not validated_data.get('thumbnail') and uploaded_images:
            validated_data['thumbnail'] = self.create_thumbnail(uploaded_images[0])
        
        # Create product
        product = Product.objects.create(**validated_data)
        
        # Add categories (support multiple categories)
        if category_ids:
            product.categories.set(category_ids)
        
        # Create product images
        for image in uploaded_images:
            ProductImage.objects.create(product=product, image=image)
        
        return product
    
    def update(self, instance, validated_data):
        """Update product with new images"""
        uploaded_images = validated_data.pop('uploaded_images', [])
        category_ids = validated_data.pop('category_ids', None)
        
        # Update slug if name changes
        if 'name' in validated_data and validated_data['name'] != instance.name:
            validated_data['slug'] = slugify(validated_data['name'])
        
        # Handle categories (support multiple categories)
        if category_ids is not None:
            instance.categories.set(category_ids)
        
        # Update product fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Add new images
        for image in uploaded_images:
            ProductImage.objects.create(product=instance, image=image)
        
        return instance


class CommentSerializer(serializers.ModelSerializer):
    """Serializer for product comments"""
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Comment
        fields = ['id', 'product', 'user', 'user_username', 'body', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at']


class VoucherSerializer(serializers.ModelSerializer):
    """Serializer for vouchers"""
    user_username = serializers.CharField(source='user.username', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = Voucher
        fields = ['id', 'product', 'product_name', 'user', 'user_username', 'code', 'created_at']
        read_only_fields = ['user', 'code', 'created_at']
