# User/tasks.py
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.db import connection
from django.utils import timezone
from datetime import datetime, timedelta
import time
from django.contrib.auth import get_user_model 
from User.models import User

@shared_task
def send_confirm_email(user_email):
    """
    Celery task to send confirmation email to user after registration.
    
    Args:
        user_email (str): The email address of the newly registered user
        
    Returns:
        bool: True if email was sent successfully
    """
    try:
        # Simulate processing time (you can remove this in production)
        time.sleep(5)
        
        subject = 'Welcome to Our Platform - Registration Confirmation'
        message = f"""
        Dear User,
        
        Thank you for registering with us!
        
        Your account has been successfully created with the email: {user_email}
        
        Please verify your email address to activate your account.
        
        If you did not create this account, please ignore this email.
        
        Best regards,
        The Team
        """
        
        from_email = settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@example.com'
        recipient_list = [user_email]
        
        # Send email (in development, this will be printed to console if EMAIL_BACKEND is console)
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            fail_silently=False,
        )
        
        print(f"✓ Confirmation email sent successfully to {user_email}")
        return True
        
    except Exception as e:
        print(f"✗ Failed to send confirmation email to {user_email}: {str(e)}")
        # Re-raise the exception so Celery can retry if configured
        raise


@shared_task
def db_health_check():
    """
    Celery Beat task to check database health every minute.
    If the database connection fails, sends an email notification to admin.
    
    Returns:
        dict: Status of the health check with details
    """
    try:
        # Attempt to execute a simple query to check database connectivity
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
        
        if result:
            print(f"✓ [DB Health Check] Database is healthy at {timezone.now()}")
            return {
                'status': 'success',
                'message': 'Database is healthy',
                'timestamp': str(timezone.now())
            }
    except Exception as e:
        # Database check failed, send email to admin
        error_message = str(e)
        print(f"✗ [DB Health Check] Database check failed at {timezone.now()}: {error_message}")
        
        try:
            # Get admin emails from user(s) with is_superuser=True
            admin_emails = User.objects.filter(is_superuser=True).values_list('email', flat=True)
            
            subject = '⚠️ Database Health Check Failed - Urgent Action Required'
            message = f"""
            ALERT: Database Health Check Failure
            
            Time: {timezone.now()}
            
            Error Details:
            {error_message}
            
            The database connection test failed. Please investigate immediately.
            
            System: {settings.DATABASES['default']['ENGINE']}
            Database: {settings.DATABASES['default']['NAME']}
            Host: {settings.DATABASES['default']['HOST']}
            
            This is an automated alert from the database monitoring system.
            """
            
            from_email = settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@example.com'
            
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=admin_emails,
                fail_silently=False,
            )
            
            print(f"✓ Alert email sent to admin at {admin_emails}")
            
        except Exception as email_error:
            print(f"✗ Failed to send alert email: {str(email_error)}")
        
        return {
            'status': 'failed',
            'message': f'Database health check failed: {error_message}',
            'timestamp': str(timezone.now())
        }


@shared_task
def signup_report():
    """
    Celery Beat task to send a daily report of users who signed up during the day.
    This task should be scheduled to run once per day (e.g., at 8:30 AM).
    
    Returns:
        dict: Report status with number of new users
    """   
    try:
        # Get current date and calculate start/end of the day
        now = timezone.now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Get all users who signed up today
        new_users = User.objects.filter(
            date_joined__gte=start_of_day,
            date_joined__lte=end_of_day
        ).order_by('date_joined')
        
        user_count = new_users.count()
        
        admin_emails = User.objects.filter(is_superuser=True).values_list('email', flat=True)
        
        # Prepare the user list for the email
        if user_count > 0:
            user_list = "\n".join([
                f"  - {user.username} ({user.email}) - Joined at: {user.date_joined.strftime('%H:%M:%S')}"
                for user in new_users
            ])
            
            subject = f'📊 Daily Signup Report - {user_count} New User(s) - {now.strftime("%Y-%m-%d")}'
            message = f"""
            Daily User Signup Report
            
            Date: {now.strftime('%Y-%m-%d')}
            Period: {start_of_day.strftime('%Y-%m-%d %H:%M:%S')} to {end_of_day.strftime('%Y-%m-%d %H:%M:%S')}
            
            Total New Users: {user_count}
            
            New Users List:
{user_list}
            
            ----------------------------------------
            This is an automated daily report from the user management system.
            """
        else:
            subject = f'📊 Daily Signup Report - No New Users - {now.strftime("%Y-%m-%d")}'
            message = f"""
            Daily User Signup Report
            
            Date: {now.strftime('%Y-%m-%d')}
            Period: {start_of_day.strftime('%Y-%m-%d %H:%M:%S')} to {end_of_day.strftime('%Y-%m-%d %H:%M:%S')}
            
            Total New Users: 0
            
            No new users signed up today.
            
            ----------------------------------------
            This is an automated daily report from the user management system.
            """
        
        # Send the email
        from_email = settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@example.com'
        
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=admin_emails,
            fail_silently=False,
        )
        
        print(f"✓ Daily signup report sent to admin. New users: {user_count}")
        
        return {
            'status': 'success',
            'message': f'Daily report sent successfully',
            'new_users_count': user_count,
            'timestamp': str(now)
        }
        
    except Exception as e:
        error_message = str(e)
        print(f"✗ Failed to generate/send daily signup report: {error_message}")
        
        return {
            'status': 'failed',
            'message': f'Failed to send daily report: {error_message}',
            'timestamp': str(timezone.now())
        }

