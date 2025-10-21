"""
Custom signals for User app
"""
from django.dispatch import Signal, receiver
from django.db.models.signals import post_save
from .models import User
from .tasks import send_confirm_email

# Custom signal for user signup
user_signed_up = Signal()


@receiver(user_signed_up)
def handle_user_signed_up(sender, user, **kwargs):
    """
    Signal handler that triggers when a user signs up.
    Sends a confirmation email asynchronously using Celery.
    
    Args:
        sender: The sender of the signal
        user: The User instance that was created
        **kwargs: Additional keyword arguments
    """
    # Trigger the Celery task to send confirmation email
    send_confirm_email.delay(user.email)
    print(f"Signal received: User {user.username} signed up. Email task queued.")
