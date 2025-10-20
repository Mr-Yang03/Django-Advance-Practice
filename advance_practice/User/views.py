from django.shortcuts import render
from django.http import HttpResponse
from .models import User
import django.contrib.messages as messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

# Create your views here.
def register(request):
    """User registration view"""
    if request.user.is_authenticated:
        return

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')

        # Validation
        if password != password2:
            messages.error(request, 'Passwords do not match.')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')

        # Create user
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            # UserProfile sẽ được tự động tạo bởi signal

            messages.success(request, 'Account created successfully! Please login.')
        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')

def user_login(request):
    """User login view"""
    if request.user.is_authenticated:
        return

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'Logged in successfully!')
        else:
            messages.error(request, 'Invalid username or password.')

@login_required
def user_logout(request):
    """User logout view"""
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, 'Logged out successfully!')