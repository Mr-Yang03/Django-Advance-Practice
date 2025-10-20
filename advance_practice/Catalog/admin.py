from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import Category, Product, ProductImage, Comment, Voucher


class ProductImageInline(admin.TabularInline):
    """Inline admin for Product Images"""
    model = ProductImage
    extra = 1
    fields = ('image', 'caption', 'image_preview')
    readonly_fields = ('image_preview',)
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 200px;" />',
                obj.image.url
            )
        return "No image"
    image_preview.short_description = 'Preview'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin configuration for Category model"""
    list_display = ('name', 'slug', 'parent', 'products_count', 'children_count', 'image_preview', 'created_at')
    list_filter = ('parent', 'created_at', 'updated_at')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)
    date_hierarchy = 'created_at'
    
    # For categories with many records, use raw_id_fields for parent selection
    raw_id_fields = ('parent',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Media', {
            'fields': ('image',)
        }),
        ('Hierarchy', {
            'fields': ('parent',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'products_count', 'children_count')
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 100px;" />',
                obj.image.url
            )
        return "No image"
    image_preview.short_description = 'Image'
    
    def products_count(self, obj):
        return obj.products.count()
    products_count.short_description = 'Products'
    products_count.admin_order_field = 'products_count'
    
    def children_count(self, obj):
        return obj.children.count()
    children_count.short_description = 'Subcategories'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related and annotations"""
        queryset = super().get_queryset(request)
        queryset = queryset.select_related('parent').annotate(
            products_count=Count('products', distinct=True)
        )
        return queryset


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Admin configuration for Product model"""
    list_display = (
        'name', 'slug', 'price', 'view_count', 
        'voucher_enabled', 'voucher_quantity', 
        'thumbnail_preview', 'images_count', 'comments_count',
        'created_at'
    )
    list_filter = (
        'voucher_enabled', 'categories', 
        'created_at', 'updated_at'
    )
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    
    # For products with many categories, use filter_horizontal for better UX
    filter_horizontal = ('categories',)
    
    # For edit lock with many users, use raw_id_fields
    raw_id_fields = ('editing_user',)
    
    # Inline for product images
    inlines = [ProductImageInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'price')
        }),
        ('Media', {
            'fields': ('thumbnail',)
        }),
        ('Categories', {
            'fields': ('categories',)
        }),
        ('Statistics', {
            'fields': ('view_count',),
            'classes': ('collapse',)
        }),
        ('Voucher Settings', {
            'fields': ('voucher_enabled', 'voucher_quantity'),
            'classes': ('collapse',)
        }),
        ('Edit Lock', {
            'fields': ('editing_user', 'edit_lock_time'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'view_count')
    
    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 100px;" />',
                obj.thumbnail.url
            )
        return "No thumbnail"
    thumbnail_preview.short_description = 'Thumbnail'
    
    def images_count(self, obj):
        return obj.images.count()
    images_count.short_description = 'Images'
    images_count.admin_order_field = 'images_count'
    
    def comments_count(self, obj):
        return obj.comments.count()
    comments_count.short_description = 'Comments'
    comments_count.admin_order_field = 'comments_count'
    
    def get_queryset(self, request):
        """Optimize queryset with prefetch_related and annotations"""
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related('categories', 'images', 'comments').annotate(
            images_count=Count('images', distinct=True),
            comments_count=Count('comments', distinct=True)
        )
        return queryset
    
    actions = ['enable_voucher', 'disable_voucher', 'reset_view_count']
    
    def enable_voucher(self, request, queryset):
        updated = queryset.update(voucher_enabled=True)
        self.message_user(request, f'{updated} products voucher enabled.')
    enable_voucher.short_description = 'Enable voucher for selected products'
    
    def disable_voucher(self, request, queryset):
        updated = queryset.update(voucher_enabled=False)
        self.message_user(request, f'{updated} products voucher disabled.')
    disable_voucher.short_description = 'Disable voucher for selected products'
    
    def reset_view_count(self, request, queryset):
        updated = queryset.update(view_count=0)
        self.message_user(request, f'{updated} products view count reset.')
    reset_view_count.short_description = 'Reset view count for selected products'


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    """Admin configuration for ProductImage model"""
    list_display = ('id', 'product', 'image_preview', 'caption', 'created_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('product__name', 'caption')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    
    # For products with many images, use raw_id_fields
    raw_id_fields = ('product',)
    
    fields = ('product', 'image', 'caption', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 200px;" />',
                obj.image.url
            )
        return "No image"
    image_preview.short_description = 'Preview'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        queryset = super().get_queryset(request)
        queryset = queryset.select_related('product')
        return queryset


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """Admin configuration for Comment model"""
    list_display = ('id', 'product', 'user', 'body_preview', 'created_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('product__name', 'user__username', 'body')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    
    # For comments with many products/users, use raw_id_fields
    raw_id_fields = ('product', 'user')
    
    fields = ('product', 'user', 'body', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    
    def body_preview(self, obj):
        return obj.body[:50] + '...' if len(obj.body) > 50 else obj.body
    body_preview.short_description = 'Comment'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        queryset = super().get_queryset(request)
        queryset = queryset.select_related('product', 'user')
        return queryset


@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    """Admin configuration for Voucher model"""
    list_display = ('code', 'product', 'user', 'created_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('code', 'product__name', 'user__username')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    
    # For vouchers with many products/users, use raw_id_fields
    raw_id_fields = ('product', 'user')
    
    fields = ('product', 'user', 'code', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        queryset = super().get_queryset(request)
        queryset = queryset.select_related('product', 'user')
        return queryset


# Customize Admin Site Header
admin.site.site_header = "Catalog Admin Panel"
admin.site.site_title = "Catalog Admin"
admin.site.index_title = "Welcome to Catalog Management"
