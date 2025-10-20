from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'categories', api_views.CategoryViewSet, basename='category')
router.register(r'products', api_views.ProductViewSet, basename='product')
router.register(r'product-images', api_views.ProductImageViewSet, basename='productimage')
router.register(r'comments', api_views.CommentViewSet, basename='comment')
router.register(r'vouchers', api_views.VoucherViewSet, basename='voucher')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    
    # Report APIs
    path('api/reports/', api_views.ReportAPIView.as_view(), name='reports'),
    path('api/reports/products-per-category/', api_views.ProductsPerCategoryReportAPIView.as_view(), name='products-per-category'),
    path('api/reports/product-views/<int:product_id>/', api_views.ProductViewsReportAPIView.as_view(), name='product-views'),
    path('api/reports/product-comments/<int:product_id>/', api_views.ProductCommentsReportAPIView.as_view(), name='product-comments'),
    path('api/reports/category-stats/', api_views.CategoryStatsReportAPIView.as_view(), name='category-stats'),
]
