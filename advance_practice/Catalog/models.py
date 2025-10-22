from django.db import models
from django.conf import settings

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']

class Category(TimeStampedModel):
    """
    Model for Product Category (Practice 1).
    """
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    
    # Request to "Upload image"
    image = models.ImageField(upload_to='categories/images/', blank=True, null=True)

    # Request to "Tree" - A category can have a parent category
    parent = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='children'
    )
    
    # --- Fields for Classical Practice (Edit Lock) ---
    
    # Request to "mark the current editing user"
    editing_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='editing_category'
    )
    # Request to "timeout, e.g., 5 minutes"
    edit_lock_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

class Product(TimeStampedModel):
    """
    Model for Product (Practice 1, 2 and Classical Practices).
    """
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Request to "thumbnail" (ảnh bìa chính)
    thumbnail = models.ImageField(upload_to='products/thumbnails/', blank=True, null=True)
    
    # Request "one or more categories"
    categories = models.ManyToManyField(
        Category, 
        related_name='products',
        blank=True
    )
    
    # --- Fields for Practice 2 (DRF Reports) ---
    
    # Request to "Total views of a product"
    view_count = models.PositiveIntegerField(default=0)

    # --- Fields for Classical Practice (Edit Lock) ---

    # Request to "mark the current editing user"
    editing_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='editing_product'
    )
    # Request to "timeout, e.g., 5 minutes"
    edit_lock_time = models.DateTimeField(null=True, blank=True)

    # --- Fields for Classical Practice (Voucher) ---

    # Request to "voucher_enabled"
    voucher_enabled = models.BooleanField(default=False)
    # Request to "voucher_quantity"
    voucher_quantity = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

class ProductImage(TimeStampedModel):
    """
    Model for Product Images (Practice 1).
    Request to "Can upload many images".
    """
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='images'
    )
    image = models.ImageField(upload_to='products/gallery/')
    caption = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Image for {self.product.name}"

class Comment(TimeStampedModel):
    """
    Model for Product Comments (Practice 2).
    Request to "Product comments".
    """
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='comments'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='comments'
    )
    body = models.TextField()

    class Meta:
        ordering = ['created_at'] # Sắp xếp bình luận cũ nhất trước

    def __str__(self):
        return f"Comment by {self.user.username} on {self.product.name}"

class Voucher(TimeStampedModel):
    """
    Model to store created Vouchers (Classical Practice).
    Request to "For 1 post, a user can have 1 voucher only."
    """
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='vouchers'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='vouchers'
    )
    code = models.CharField(max_length=255, unique=True, db_index=True)

    class Meta:
        # Ensure 1 user can only receive 1 voucher for 1 product
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'user'], 
                name='unique_voucher_per_user_product'
            )
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Voucher {self.code} for {self.user.username} on {self.product.name}"