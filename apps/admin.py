from django.contrib import admin
from django.contrib.admin import TabularInline, ModelAdmin
from django.contrib.auth.admin import UserAdmin
from django.db import transaction
from django.utils import timezone

from apps.models import User, Category, Product, ProductImage, Order, District, Region, CompetitionResult, Competition, \
    Withdrawal


@admin.register(User)
class UserAdmin(UserAdmin):
    ordering = ('phone_number',)
    list_display = ('phone_number', 'first_name', 'last_name', 'region', 'district',
                    'is_operator', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_operator', 'region', 'district')
    list_editable = ('is_operator',)
    search_fields = ('phone_number', 'first_name', 'last_name', 'telegram_id')

    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('Shaxsiy ma\'lumotlar', {'fields': ('first_name', 'last_name', 'region', 'district', 'telegram_id', 'bio')}),
        ('Ruxsatlar', {'fields': ('is_active', 'is_operator', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Muhim sanalar', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'password', 'first_name', 'last_name', 'region', 'district',
                       'is_active', 'is_operator', 'is_staff'),
        }),
    )

@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ('id', 'title', 'slug', 'parent', 'image')
    prepopulated_fields = {'slug': ('title',)}
    list_filter = ('parent',)
    search_fields = ('title', 'slug')


class ProductImageInline(TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = ('id', 'title', 'category', 'price', 'delivery_price', 'stock_quantity', 'created_at')
    prepopulated_fields = {'slug': ('title',)}
    list_filter = ('category', 'created_at')
    search_fields = ('title', 'description')
    inlines = [ProductImageInline]


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = ('id', 'full_name', 'phone_number', 'product', 'quantity', 'total_price', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('full_name', 'phone_number')
    list_editable = ('status',)


@admin.register(Region)
class RegionAdmin(ModelAdmin):
    list_display = ('id', 'title')
    search_fields = ('title',)


@admin.register(District)
class DistrictAdmin(ModelAdmin):
    list_display = ('id', 'title', 'region')
    list_filter = ('region',)
    search_fields = ('title',)


@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title',)


@admin.register(CompetitionResult)
class CompetitionResultAdmin(admin.ModelAdmin):
    list_display = ('competition', 'display_name', 'sold_count', 'updated_at')
    list_filter = ('competition',)
    search_fields = ('display_name',)
    ordering = ('-sold_count',)


@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'card_number', 'amount', 'status', 'created_at', 'processed_at')
    list_filter = ('status', 'type')
    search_fields = ('card_number', 'user__phone_number')
    readonly_fields = ('created_at',)
    actions = ['mark_completed', 'mark_rejected']

    def mark_completed(self, request, queryset):
        processed = 0
        for withdrawal_id in queryset.values_list('pk', flat=True):
            with transaction.atomic():
                # Har bir so'rovni alohida qatorlar bo'yicha qulflab qayta o'qiymiz —
                # shu orqali bir xil so'rov ikki marta qayta ishlanmaydi (idempotentlik)
                # va bir vaqtda bir nechta admin bosgan taqdirda ham balans buzilmaydi.
                withdrawal = Withdrawal.objects.select_for_update().get(pk=withdrawal_id)
                if withdrawal.status not in (Withdrawal.Status.PENDING, Withdrawal.Status.PROCESSING):
                    continue

                user = User.objects.select_for_update().get(pk=withdrawal.user_id)
                user.pending_balance -= withdrawal.amount
                user.save(update_fields=['pending_balance'])

                withdrawal.status = Withdrawal.Status.COMPLETED
                withdrawal.processed_at = timezone.now()
                withdrawal.save(update_fields=['status', 'processed_at'])
                processed += 1

        self.message_user(request, f"{processed} ta so'rov 'Bajarildi' deb belgilandi.")

    mark_completed.short_description = "Tanlanganlarni 'Bajarildi' deb belgilash"

    def mark_rejected(self, request, queryset):
        processed = 0
        for withdrawal_id in queryset.values_list('pk', flat=True):
            with transaction.atomic():
                withdrawal = Withdrawal.objects.select_for_update().get(pk=withdrawal_id)
                if withdrawal.status not in (Withdrawal.Status.PENDING, Withdrawal.Status.PROCESSING):
                    continue

                user = User.objects.select_for_update().get(pk=withdrawal.user_id)
                user.pending_balance -= withdrawal.amount
                user.main_balance += withdrawal.amount
                user.save(update_fields=['main_balance', 'pending_balance'])

                withdrawal.status = Withdrawal.Status.REJECTED
                withdrawal.processed_at = timezone.now()
                withdrawal.save(update_fields=['status', 'processed_at'])
                processed += 1

        self.message_user(request, f"{processed} ta so'rov rad etildi.")

    mark_rejected.short_description = "Tanlanganlarni rad etish"