"""
Edit Lock API Views for Products and Categories
Implements the "Only one user can access post edit" requirement
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
from .models import Product, Category


# Lock timeout duration (5 minutes)
LOCK_TIMEOUT = timedelta(minutes=5)


def check_lock_expired(obj):
    """Check if the edit lock has expired"""
    if obj.edit_lock_time:
        return timezone.now() > obj.edit_lock_time
    return True


def clear_expired_lock(obj):
    """Clear the lock if it has expired"""
    if check_lock_expired(obj):
        obj.editing_user = None
        obj.edit_lock_time = None
        obj.save(update_fields=['editing_user', 'edit_lock_time'])
        return True
    return False


@extend_schema(
    tags=['Products'],
    summary='Request edit lock for a product',
    description='''
    Request permission to edit a product. 
    - Returns 200 if lock is granted
    - Returns 409 if another user is currently editing
    - Automatically clears expired locks (>5 minutes)
    ''',
    responses={
        200: OpenApiResponse(
            description='Lock granted',
            examples=[
                OpenApiExample(
                    'Success',
                    value={
                        'status': 'allowed',
                        'message': 'You can now edit this product',
                        'editing_user': 'username',
                        'lock_expires_at': '2025-10-22T10:30:00Z'
                    }
                )
            ]
        ),
        409: OpenApiResponse(
            description='Another user is editing',
            examples=[
                OpenApiExample(
                    'Conflict',
                    value={
                        'status': 'locked',
                        'message': 'This product is being edited by another user',
                        'editing_user': 'other_user',
                        'lock_expires_at': '2025-10-22T10:30:00Z'
                    }
                )
            ]
        ),
        404: OpenApiResponse(description='Product not found')
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def product_edit_lock(request, product_id):
    """
    API: POST /catalog/api/products/{product_id}/editable/me
    Request permission to edit a product with row-level locking
    """
    from django.db import transaction
    
    # Use transaction with select_for_update to prevent race conditions
    with transaction.atomic():
        try:
            # Lock the product row - blocks other transactions until commit
            product = Product.objects.select_for_update().get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Clear expired lock first
        if check_lock_expired(product):
            product.editing_user = None
            product.edit_lock_time = None
        
        # Check if product is being edited
        if product.editing_user:
            # If the same user, extend the lock
            if product.editing_user == request.user:
                product.edit_lock_time = timezone.now() + LOCK_TIMEOUT
                product.save(update_fields=['edit_lock_time'])
                
                return Response({
                    'status': 'allowed',
                    'message': 'You can continue editing this product',
                    'editing_user': request.user.username,
                    'lock_expires_at': product.edit_lock_time.isoformat(),
                    'lock_duration_seconds': int(LOCK_TIMEOUT.total_seconds())
                }, status=status.HTTP_200_OK)
            else:
                # Another user is editing
                return Response({
                    'status': 'locked',
                    'message': 'This product is being edited by another user',
                    'editing_user': product.editing_user.username,
                    'lock_expires_at': product.edit_lock_time.isoformat() if product.edit_lock_time else None
                }, status=status.HTTP_409_CONFLICT)
        
        # Lock is available, grant it
        product.editing_user = request.user
        product.edit_lock_time = timezone.now() + LOCK_TIMEOUT
        product.save(update_fields=['editing_user', 'edit_lock_time'])
        
        return Response({
            'status': 'allowed',
            'message': 'You can now edit this product',
            'editing_user': request.user.username,
            'lock_expires_at': product.edit_lock_time.isoformat(),
            'lock_duration_seconds': int(LOCK_TIMEOUT.total_seconds())
        }, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Products'],
    summary='Release edit lock for a product',
    description='''
    Release the edit lock after saving or canceling edit.
    Only the user who has the lock can release it.
    ''',
    responses={
        200: OpenApiResponse(
            description='Lock released',
            examples=[
                OpenApiExample(
                    'Success',
                    value={'status': 'released', 'message': 'Edit lock released successfully'}
                )
            ]
        ),
        403: OpenApiResponse(description='You do not have the lock'),
        404: OpenApiResponse(description='Product not found')
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def product_edit_release(request, product_id):
    """
    API: POST /catalog/api/products/{product_id}/editable/release
    Release the edit lock
    """
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response(
            {'error': 'Product not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if the current user has the lock
    if product.editing_user and product.editing_user != request.user:
        return Response({
            'status': 'forbidden',
            'message': 'You do not have the edit lock for this product'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Release the lock
    product.editing_user = None
    product.edit_lock_time = None
    product.save(update_fields=['editing_user', 'edit_lock_time'])
    
    return Response({
        'status': 'released',
        'message': 'Edit lock released successfully'
    }, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Products'],
    summary='Check edit lock status',
    description='Check if a product can be edited and who is currently editing',
    responses={
        200: OpenApiResponse(
            description='Lock status',
            examples=[
                OpenApiExample(
                    'Available',
                    value={
                        'can_edit': True,
                        'editing_user': None,
                        'lock_expires_at': None
                    }
                ),
                OpenApiExample(
                    'Locked',
                    value={
                        'can_edit': False,
                        'editing_user': 'username',
                        'lock_expires_at': '2025-10-22T10:30:00Z'
                    }
                )
            ]
        )
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def product_edit_maintain(request, product_id):
    """
    API: GET /catalog/api/products/{product_id}/editable/maintain
    Check the current edit lock status
    """
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response(
            {'error': 'Product not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Clear expired lock
    clear_expired_lock(product)
    
    can_edit = (not product.editing_user) or (product.editing_user == request.user)
    
    return Response({
        'can_edit': can_edit,
        'editing_user': product.editing_user.username if product.editing_user else None,
        'lock_expires_at': product.edit_lock_time.isoformat() if product.edit_lock_time else None,
        'is_you': product.editing_user == request.user if product.editing_user else False
    }, status=status.HTTP_200_OK)


# ==================== Category Edit Lock APIs ====================

@extend_schema(
    tags=['Categories'],
    summary='Request edit lock for a category',
    description='''
    Request permission to edit a category. 
    - Returns 200 if lock is granted
    - Returns 409 if another user is currently editing
    - Automatically clears expired locks (>5 minutes)
    ''',
    responses={
        200: OpenApiResponse(description='Lock granted'),
        409: OpenApiResponse(description='Another user is editing'),
        404: OpenApiResponse(description='Category not found')
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def category_edit_lock(request, category_id):
    """
    API: POST /catalog/api/categories/{category_id}/editable/me
    Request permission to edit a category with row-level locking
    """
    from django.db import transaction
    
    # Use transaction with select_for_update to prevent race conditions
    with transaction.atomic():
        try:
            # Lock the category row - blocks other transactions until commit
            category = Category.objects.select_for_update().get(id=category_id)
        except Category.DoesNotExist:
            return Response(
                {'error': 'Category not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Clear expired lock first
        if check_lock_expired(category):
            category.editing_user = None
            category.edit_lock_time = None
        
        # Check if category is being edited
        if category.editing_user:
            # If the same user, extend the lock
            if category.editing_user == request.user:
                category.edit_lock_time = timezone.now() + LOCK_TIMEOUT
                category.save(update_fields=['edit_lock_time'])
                
                return Response({
                    'status': 'allowed',
                    'message': 'You can continue editing this category',
                    'editing_user': request.user.username,
                    'lock_expires_at': category.edit_lock_time.isoformat(),
                    'lock_duration_seconds': int(LOCK_TIMEOUT.total_seconds())
                }, status=status.HTTP_200_OK)
            else:
                # Another user is editing
                return Response({
                    'status': 'locked',
                    'message': 'This category is being edited by another user',
                    'editing_user': category.editing_user.username,
                    'lock_expires_at': category.edit_lock_time.isoformat() if category.edit_lock_time else None
                }, status=status.HTTP_409_CONFLICT)
    
    # Lock is available, grant it
    category.editing_user = request.user
    category.edit_lock_time = timezone.now() + LOCK_TIMEOUT
    category.save(update_fields=['editing_user', 'edit_lock_time'])
    
    return Response({
        'status': 'allowed',
        'message': 'You can now edit this category',
        'editing_user': request.user.username,
        'lock_expires_at': category.edit_lock_time.isoformat(),
        'lock_duration_seconds': int(LOCK_TIMEOUT.total_seconds())
    }, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Categories'],
    summary='Release edit lock for a category',
    description='Release the edit lock after saving or canceling edit',
    responses={
        200: OpenApiResponse(description='Lock released'),
        403: OpenApiResponse(description='You do not have the lock'),
        404: OpenApiResponse(description='Category not found')
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def category_edit_release(request, category_id):
    """
    API: POST /catalog/api/categories/{category_id}/editable/release
    Release the edit lock
    """
    try:
        category = Category.objects.get(id=category_id)
    except Category.DoesNotExist:
        return Response(
            {'error': 'Category not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if the current user has the lock
    if category.editing_user and category.editing_user != request.user:
        return Response({
            'status': 'forbidden',
            'message': 'You do not have the edit lock for this category'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Release the lock
    category.editing_user = None
    category.edit_lock_time = None
    category.save(update_fields=['editing_user', 'edit_lock_time'])
    
    return Response({
        'status': 'released',
        'message': 'Edit lock released successfully'
    }, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Categories'],
    summary='Check edit lock status',
    description='Check if a category can be edited and who is currently editing',
    responses={
        200: OpenApiResponse(description='Lock status')
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def category_edit_maintain(request, category_id):
    """
    API: GET /catalog/api/categories/{category_id}/editable/maintain
    Check the current edit lock status
    """
    try:
        category = Category.objects.get(id=category_id)
    except Category.DoesNotExist:
        return Response(
            {'error': 'Category not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Clear expired lock
    clear_expired_lock(category)
    
    can_edit = (not category.editing_user) or (category.editing_user == request.user)
    
    return Response({
        'can_edit': can_edit,
        'editing_user': category.editing_user.username if category.editing_user else None,
        'lock_expires_at': category.edit_lock_time.isoformat() if category.edit_lock_time else None,
        'is_you': category.editing_user == request.user if category.editing_user else False
    }, status=status.HTTP_200_OK)


# ==================== Release Stale Locks on Page Load ====================

@extend_schema(
    tags=['Products'],
    summary='Release all product locks held by current user',
    description='''
    Release all product edit locks currently held by the authenticated user.
    This is called automatically when the page loads to clean up stale locks
    from page refreshes or browser crashes.
    ''',
    responses={
        200: OpenApiResponse(
            description='Locks released',
            examples=[
                OpenApiExample(
                    'Success',
                    value={
                        'status': 'success',
                        'message': 'Released 2 product locks',
                        'released_count': 2
                    }
                )
            ]
        )
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def release_my_product_locks(request):
    """
    API: POST /catalog/api/products/release-my-locks/
    Release all product locks held by current user
    """
    # Find all products locked by current user
    locked_products = Product.objects.filter(editing_user=request.user)
    count = locked_products.count()
    
    # Release all locks
    locked_products.update(editing_user=None, edit_lock_time=None)
    
    return Response({
        'status': 'success',
        'message': f'Released {count} product lock(s)',
        'released_count': count
    }, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Categories'],
    summary='Release all category locks held by current user',
    description='''
    Release all category edit locks currently held by the authenticated user.
    This is called automatically when the page loads to clean up stale locks
    from page refreshes or browser crashes.
    ''',
    responses={
        200: OpenApiResponse(
            description='Locks released',
            examples=[
                OpenApiExample(
                    'Success',
                    value={
                        'status': 'success',
                        'message': 'Released 1 category lock',
                        'released_count': 1
                    }
                )
            ]
        )
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def release_my_category_locks(request):
    """
    API: POST /catalog/api/categories/release-my-locks/
    Release all category locks held by current user
    """
    # Find all categories locked by current user
    locked_categories = Category.objects.filter(editing_user=request.user)
    count = locked_categories.count()
    
    # Release all locks
    locked_categories.update(editing_user=None, edit_lock_time=None)
    
    return Response({
        'status': 'success',
        'message': f'Released {count} category lock(s)',
        'released_count': count
    }, status=status.HTTP_200_OK)
