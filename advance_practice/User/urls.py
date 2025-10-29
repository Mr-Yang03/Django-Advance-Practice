from django.urls import path
from . import views, api_views
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # Template-based views
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('delete-account/', views.delete_account, name='delete_account'),
    
    # API endpoints
    path('api/register/', api_views.RegisterAPIView.as_view(), name='api_register'),
    path('api/login/', api_views.LoginAPIView.as_view(), name='api_login'),
    path('api/logout/', api_views.LogoutAPIView.as_view(), name='api_logout'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/profile/', api_views.UserProfileAPIView.as_view(), name='api_profile'),
    path('api/change-password/', api_views.ChangePasswordAPIView.as_view(), name='api_change_password'),
    path('api/delete-account/', api_views.UserDeleteAPIView.as_view(), name='api_user_delete'),
    path('api/users/', api_views.UserListAPIView.as_view(), name='api_user_list'),
]