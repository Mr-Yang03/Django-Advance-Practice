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
]
