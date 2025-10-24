from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from .models import User
from .serializers import (
    UserSerializer, 
    RegisterSerializer, 
    LoginSerializer,
    ChangePasswordSerializer
)
from .signals import user_signed_up


@extend_schema(
    tags=['Authentication'],
    summary='User Registration',
    description='Register a new user account. Returns user data and JWT tokens.',
    request=RegisterSerializer,
    responses={
        201: {
            'description': 'User successfully registered',
            'examples': {
                'application/json': {
                    'message': 'User registered successfully. Confirmation email will be sent shortly.',
                    'user': {
                        'id': 1,
                        'username': 'testuser',
                        'email': 'test@example.com',
                        'first_name': 'Test',
                        'last_name': 'User'
                    },
                    'tokens': {
                        'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGc...',
                        'access': 'eyJ0eXAiOiJKV1QiLCJhbGc...'
                    }
                }
            }
        },
        400: {'description': 'Bad request - validation errors'}
    },
    examples=[
        OpenApiExample(
            'Registration Example',
            value={
                'username': 'testuser',
                'email': 'test@example.com',
                'password': 'SecurePass123!',
                'password2': 'SecurePass123!',
                'first_name': 'Test',
                'last_name': 'User'
            },
            request_only=True
        )
    ]
)
@method_decorator(csrf_exempt, name='dispatch')
class RegisterAPIView(generics.CreateAPIView):
    """
    API endpoint for user registration
    POST /api/register/
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Emit custom signal for user signup
        user_signed_up.send(sender=self.__class__, user=user)
        
        # Generate tokens for the new user
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'User registered successfully. Confirmation email will be sent shortly.',
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=['Authentication'],
    summary='User Login',
    description='Authenticate user and get JWT tokens',
    request=LoginSerializer,
    responses={
        200: {
            'description': 'Login successful',
            'examples': {
                'application/json': {
                    'message': 'Login successful',
                    'user': {
                        'id': 1,
                        'username': 'testuser',
                        'email': 'test@example.com'
                    },
                    'tokens': {
                        'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGc...',
                        'access': 'eyJ0eXAiOiJKV1QiLCJhbGc...'
                    }
                }
            }
        },
        401: {'description': 'Invalid credentials'},
        403: {'description': 'Account is disabled'}
    },
    examples=[
        OpenApiExample(
            'Login Example',
            value={
                'username': 'testuser',
                'password': 'SecurePass123!'
            },
            request_only=True
        )
    ]
)
@method_decorator(csrf_exempt, name='dispatch')
class LoginAPIView(APIView):
    """
    API endpoint for user login
    POST /api/login/
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        
        user = authenticate(username=username, password=password)
        
        if user is not None:
            if user.is_active:
                # Generate tokens
                refresh = RefreshToken.for_user(user)
                
                return Response({
                    'message': 'Login successful',
                    'user': UserSerializer(user).data,
                    'tokens': {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Account is disabled'
                }, status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({
                'error': 'Invalid username or password'
            }, status=status.HTTP_401_UNAUTHORIZED)


@extend_schema(
    tags=['Authentication'],
    summary='User Logout',
    description='Logout user by blacklisting the refresh token',
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'refresh_token': {'type': 'string', 'description': 'JWT refresh token to blacklist'}
            },
            'required': ['refresh_token']
        }
    },
    responses={
        205: {'description': 'Logout successful'},
        400: {'description': 'Bad request - token required or invalid'}
    },
    examples=[
        OpenApiExample(
            'Logout Example',
            value={'refresh_token': 'eyJ0eXAiOiJKV1QiLCJhbGc...'},
            request_only=True
        )
    ]
)
class LogoutAPIView(APIView):
    """
    API endpoint for user logout
    POST /api/logout/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
                return Response({
                    'message': 'Logout successful'
                }, status=status.HTTP_205_RESET_CONTENT)
            else:
                return Response({
                    'error': 'Refresh token is required'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['User Profile'],
    summary='Get/Update User Profile',
    description='Retrieve or update the authenticated user profile',
    responses={
        200: UserSerializer,
        401: {'description': 'Authentication required'}
    }
)
class UserProfileAPIView(generics.RetrieveUpdateAPIView):
    """
    API endpoint to get and update user profile
    GET /api/profile/
    PUT/PATCH /api/profile/
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user


@extend_schema(
    tags=['User Profile'],
    summary='Change Password',
    description='Change the authenticated user password',
    request=ChangePasswordSerializer,
    responses={
        200: {
            'description': 'Password changed successfully',
            'examples': {
                'application/json': {
                    'message': 'Password changed successfully'
                }
            }
        },
        400: {'description': 'Bad request - old password incorrect or validation errors'}
    },
    examples=[
        OpenApiExample(
            'Change Password Example',
            value={
                'old_password': 'OldPass123!',
                'new_password': 'NewPass123!',
                'new_password2': 'NewPass123!'
            },
            request_only=True
        )
    ]
)
class ChangePasswordAPIView(APIView):
    """
    API endpoint to change user password
    POST /api/change-password/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        
        # Check old password
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({
                'error': 'Old password is incorrect'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Set new password
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({
            'message': 'Password changed successfully'
        }, status=status.HTTP_200_OK)


@extend_schema(
    tags=['User Management'],
    summary='List All Users',
    description='Get list of all users (Admin only)',
    responses={
        200: UserSerializer(many=True),
        403: {'description': 'Admin permission required'}
    }
)
class UserListAPIView(generics.ListAPIView):
    """
    API endpoint to list all users (admin only)
    GET /api/users/
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]
