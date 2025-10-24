from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views, edit_lock_views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'categories', api_views.CategoryViewSet, basename='category')
router.register(r'products', api_views.ProductViewSet, basename='product')
router.register(r'product-images', api_views.ProductImageViewSet, basename='productimage')
router.register(r'comments', api_views.CommentViewSet, basename='comment')
router.register(r'vouchers', api_views.VoucherViewSet, basename='voucher')

urlpatterns = [
    # Edit Lock APIs for Products (MUST be before router to avoid conflict)
    path('api/products/release-my-locks/', edit_lock_views.release_my_product_locks, name='release-my-product-locks'),
    path('api/products/<int:product_id>/editable/me/', edit_lock_views.product_edit_lock, name='product-edit-lock'),
    path('api/products/<int:product_id>/editable/release/', edit_lock_views.product_edit_release, name='product-edit-release'),
    path('api/products/<int:product_id>/editable/maintain/', edit_lock_views.product_edit_maintain, name='product-edit-maintain'),
    
    # Edit Lock APIs for Categories (MUST be before router to avoid conflict)
    path('api/categories/release-my-locks/', edit_lock_views.release_my_category_locks, name='release-my-category-locks'),
    path('api/categories/<int:category_id>/editable/me/', edit_lock_views.category_edit_lock, name='category-edit-lock'),
    path('api/categories/<int:category_id>/editable/release/', edit_lock_views.category_edit_release, name='category-edit-release'),
    path('api/categories/<int:category_id>/editable/maintain/', edit_lock_views.category_edit_maintain, name='category-edit-maintain'),
    
    # Router URLs (include AFTER specific paths)
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    
    # Report APIs
    path('api/reports/', api_views.ReportAPIView.as_view(), name='reports'),
    path('api/reports/products-per-category/', api_views.ProductsPerCategoryReportAPIView.as_view(), name='products-per-category'),
    path('api/reports/product-views/<int:product_id>/', api_views.ProductViewsReportAPIView.as_view(), name='product-views'),
    path('api/reports/product-comments/<int:product_id>/', api_views.ProductCommentsReportAPIView.as_view(), name='product-comments'),
    path('api/reports/category-stats/', api_views.CategoryStatsReportAPIView.as_view(), name='category-stats'),
]
