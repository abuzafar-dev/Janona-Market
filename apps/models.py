import uuid
from django.contrib.auth.models import AbstractUser
from django.db.models import Model
from django.db.models.deletion import SET_NULL, CASCADE
from django.db.models.enums import TextChoices
from django.db.models.fields import (
    CharField, DateTimeField, TextField, SlugField,
    DecimalField, BooleanField, PositiveIntegerField
)
from django.db.models.fields.files import ImageField
from django.db.models.fields.related import ForeignKey
from django.utils.text import slugify
from django.contrib.auth.base_user import BaseUserManager
from django.db.models.indexes import Index
from django.utils import timezone


class Region(Model):
    title = CharField(max_length=100)

    def __str__(self):
        return self.title


class District(Model):
    title = CharField(max_length=100)
    region = ForeignKey(Region, on_delete=CASCADE, related_name='districts')

    def __str__(self):
        return self.title


class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError("Telefon raqam kiritilishi shart")
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser is_staff=True bo'lishi shart.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser is_superuser=True bo'lishi shart.")

        return self.create_user(phone_number, password, **extra_fields)


class User(AbstractUser):
    username = None
    phone_number = CharField(max_length=20, unique=True)
    first_name = CharField(max_length=50, blank=True)
    last_name = CharField(max_length=50, blank=True)
    region = ForeignKey(Region, on_delete=SET_NULL, null=True, blank=True)
    district = ForeignKey(District, on_delete=SET_NULL, null=True, blank=True)
    telegram_id = CharField(max_length=100, blank=True, null=True)
    bio = TextField(blank=True, null=True)
    created_at = DateTimeField(auto_now_add=True)
    is_operator = BooleanField(default=False)
    referred_by = ForeignKey('self', on_delete=SET_NULL, null=True, blank=True, related_name='referrals')

    main_balance = DecimalField(max_digits=12, decimal_places=0, default=0)
    pending_balance = DecimalField(max_digits=12, decimal_places=0, default=0)
    coins = PositiveIntegerField(default=0)
    api_key = CharField(max_length=100, default=uuid.uuid4, unique=True)

    objects = CustomUserManager()
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.phone_number


class Category(Model):
    title = CharField(max_length=255, null=True, blank=True)
    slug = SlugField(max_length=255, unique=True, blank=True, null=True)
    parent = ForeignKey('self', on_delete=SET_NULL, null=True, blank=True, related_name='subcategories')
    image = ImageField(upload_to='categories/', null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name_plural = "Categories"


class Product(Model):
    category = ForeignKey(Category, on_delete=SET_NULL, null=True, blank=True, related_name='products')
    title = CharField(max_length=255)
    slug = SlugField(max_length=255, unique=True, blank=True)
    description = TextField(blank=True)
    price = DecimalField(max_digits=12, decimal_places=0)
    delivery_price = DecimalField(max_digits=12, decimal_places=0, default=0)
    stock_quantity = PositiveIntegerField(default=0)
    image = ImageField(upload_to='products/', null=True, blank=True)
    created_at = DateTimeField(auto_now_add=True)
    telegram_message_id = PositiveIntegerField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class ProductImage(Model):
    product = ForeignKey(Product, on_delete=CASCADE, related_name='images')
    image = ImageField(upload_to='products/gallery/')
    order = PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Image for {self.product.title}"


class Funnel(Model):
    title = CharField(max_length=255)
    product = ForeignKey(Product, on_delete=CASCADE, related_name='funnels')
    owner = ForeignKey('User', on_delete=CASCADE, related_name='owned_funnels', null=True, blank=True)
    slug = SlugField(max_length=255, unique=True, blank=True)
    discount_price = DecimalField(max_digits=12, decimal_places=0, null=True, blank=True)
    is_active = BooleanField(default=True)
    views_count = PositiveIntegerField(default=0)
    created_at = DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug and self.title:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.product.title})"
class Order(Model):
    class Status(TextChoices):
        NEW = 'new', 'Yangi'
        PACKING = 'packing', 'Qadoqlash'
        LATER = 'later', 'Keyin oladi'
        RETURNED = 'returned', 'Qaytib keldi'
        CANCELED = 'cancelled', 'Bekor qilindi'
        HOLD = 'hold', 'Hold'
        ARCHIVE = 'archive', 'Arxiv'
        DELIVERING = 'delivering', 'Yetkazilmoqda'
        DELIVERED = 'delivered', 'Yetkazildi'

    status = CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    user = ForeignKey(User, on_delete=SET_NULL, null=True, blank=True, related_name='orders')
    funnel = ForeignKey(Funnel, on_delete=SET_NULL, null=True, blank=True, related_name='orders')
    product = ForeignKey(Product, on_delete=SET_NULL, null=True, blank=True, related_name='orders')
    quantity = PositiveIntegerField(default=1)
    full_name = CharField(max_length=255)
    phone_number = CharField(max_length=20)
    total_price = DecimalField(max_digits=12, decimal_places=0)
    shipping_address = TextField(blank=True, null=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)


    operator = ForeignKey(User, on_delete=SET_NULL, null=True, blank=True, related_name='handled_orders')
    region = ForeignKey(Region, on_delete=SET_NULL, null=True, blank=True, related_name='+')
    district = ForeignKey(District, on_delete=SET_NULL, null=True, blank=True, related_name='+')


    def __str__(self):
        return f"Order #{self.id} - {self.full_name}"


    @property
    def ui_status(self):
        mapping = {
            'new': 'new', 'packing': 'packaging', 'delivering': 'shipping',
            'delivered': 'delivered', 'later': 'pickup_later', 'hold': 'hold',
            'returned': 'returned', 'cancelled': 'cancelled', 'archive': 'archive',
        }
        return mapping.get(self.status, self.status)
class Survey(Model):
    class Status(TextChoices):
        NEW = 'new', 'Yangi'
        PROCESSING = 'processing', 'Jarayonda'
        CONFIRMED = 'confirmed', 'Tasdiqlandi'
        REJECTED = 'rejected', 'Rad etildi'
        NO_ANSWER = 'no_answer', 'Javob bermadi'

    operator = ForeignKey(User, on_delete=SET_NULL, null=True, related_name='surveys')
    funnel = ForeignKey(Funnel, on_delete=SET_NULL, null=True, blank=True, related_name='surveys')
    buyer_name = CharField(max_length=255)
    region = ForeignKey(Region, on_delete=SET_NULL, null=True, blank=True)
    phone_number = CharField(max_length=20)
    status = CharField(max_length=20, choices=Status.choices, default='new')
    comment = TextField(blank=True, null=True)
    created_at = DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"So'rovnoma #{self.id} - {self.buyer_name}"


class Withdrawal(Model):
    class Type(TextChoices):
        MONEY = 'money', 'Pul'
        COIN = 'coin', 'Tanga'

    class Status(TextChoices):
        PENDING = 'pending', 'Kutilmoqda'
        PROCESSING = 'processing', 'Jarayonda'
        COMPLETED = 'completed', 'Bajarildi'
        REJECTED = 'rejected', 'Rad etildi'

    user = ForeignKey(User, on_delete=CASCADE, related_name='withdrawals')
    type = CharField(max_length=10, choices=Type.choices, default='money')
    card_number = CharField(max_length=20)
    amount = DecimalField(max_digits=12, decimal_places=0)
    status = CharField(max_length=20, choices=Status.choices, default='pending')
    message = CharField(max_length=255, blank=True, null=True)
    receipt = ImageField(upload_to='withdrawals/receipts/', blank=True, null=True)
    created_at = DateTimeField(auto_now_add=True)
    processed_at = DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.phone_number} - {self.amount} so'm ({self.status})"


class Competition(Model):
    title = CharField(max_length=255)
    image = ImageField(upload_to='competition/')
    description = TextField(blank=True)
    start_date = DateTimeField()
    end_date = DateTimeField()
    is_active = BooleanField(default=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return self.title

    @property
    def is_finished(self):
        return timezone.now() > self.end_date


class CompetitionResult(Model):
    competition = ForeignKey(Competition, on_delete=CASCADE, related_name='results')
    user = ForeignKey('User', on_delete=SET_NULL, null=True, blank=True, related_name='competition_results')
    display_name = CharField(max_length=255, blank=True)
    sold_count = PositiveIntegerField(default=0)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-sold_count']
        unique_together = ('competition', 'user')
        indexes = [Index(fields=['competition', '-sold_count'])]

    def __str__(self):
        return f"{self.display_name or self.user} — {self.sold_count}"
