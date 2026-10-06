"""Buyurtma, zaxira, komissiya va reyting bilan bog'liq domen mantig'i.

Views'lar bu yerdagi funksiyalarni chaqiradi va faqat so'rov/javob (HTTP)
qatlami bilan shug'ullanadi — balans, zaxira va statusga oid qoidalar
shu yerda saqlanadi.
"""
from django.db import transaction
from django.db.models import Count, F, Q

from apps.models import CompetitionResult, Order, Product, User


def clean_phone_number(phone):
    if phone:
        return phone.replace(' ', '').replace('(', '').replace(')', '').replace('-', '')
    return ''


def recalculate_competition_results(competition):
    excluded = [Order.Status.CANCELED, Order.Status.RETURNED]

    leaderboard = User.objects.filter(owned_funnels__isnull=False).annotate(
        sold_count=Count(
            'owned_funnels__orders',
            filter=Q(
                owned_funnels__orders__created_at__range=(competition.start_date, competition.end_date)
            ) & ~Q(owned_funnels__orders__status__in=excluded),
            distinct=True,
        )
    ).filter(sold_count__gt=0)

    for user in leaderboard:
        CompetitionResult.objects.update_or_create(
            competition=competition,
            user=user,
            defaults={
                'display_name': f"{user.first_name} {user.last_name}".strip() or user.phone_number,
                'sold_count': user.sold_count,
            },
        )


def reserve_stock(product, quantity):
    """Mahsulot zaxirasini atomik tarzda kamaytiradi. Agar yetarli zaxira
    bo'lmasa (boshqa buyurtma bilan poyga holatida ham), False qaytaradi va
    zaxira o'zgarmaydi."""
    updated = Product.objects.filter(pk=product.pk, stock_quantity__gte=quantity).update(
        stock_quantity=F('stock_quantity') - quantity
    )
    if updated:
        product.stock_quantity -= quantity
    return bool(updated)


def release_stock(order):
    """Bekor qilingan/qaytarilgan buyurtma uchun avval kamaytirilgan zaxirani
    qaytaradi. `stock_restocked` bayrog'i orqali idempotent — bitta buyurtma
    zaxirani ikki marta qaytarib bera olmaydi."""
    if not order.product_id or not order.stock_deducted or order.stock_restocked:
        return
    with transaction.atomic():
        locked_order = Order.objects.select_for_update().get(pk=order.pk)
        if not locked_order.stock_deducted or locked_order.stock_restocked:
            return
        Product.objects.filter(pk=order.product_id).update(
            stock_quantity=F('stock_quantity') + locked_order.quantity
        )
        Order.objects.filter(pk=order.pk).update(stock_restocked=True)
    order.stock_restocked = True


def credit_commission(order):
    """Yetkazib berilgan buyurtma uchun oqim egasiga komissiya yozadi.
    `commission_paid` bayrog'i orqali idempotent — bitta buyurtma uchun
    komissiya ikki marta to'lanmaydi, hatto status qayta 'delivered' bo'lsa ham."""
    if order.commission_paid or not order.funnel_id or not order.funnel.owner_id:
        return
    commission = (order.funnel.commission or 0) * order.quantity
    if commission <= 0:
        return
    with transaction.atomic():
        locked_order = Order.objects.select_for_update().get(pk=order.pk)
        if locked_order.commission_paid:
            return
        owner = User.objects.select_for_update().get(pk=order.funnel.owner_id)
        owner.main_balance += commission
        owner.save(update_fields=['main_balance'])
        Order.objects.filter(pk=order.pk).update(commission_paid=True, commission_amount=commission)
    order.commission_paid = True
    order.commission_amount = commission


def reverse_commission(order):
    """Yetkazilgach qaytarilgan/bekor qilingan buyurtma uchun avval yozilgan
    komissiyani sotuvchi balansidan qaytarib oladi (idempotent)."""
    if not order.commission_paid or not order.funnel_id or not order.funnel.owner_id:
        return
    with transaction.atomic():
        locked_order = Order.objects.select_for_update().get(pk=order.pk)
        if not locked_order.commission_paid:
            return
        owner = User.objects.select_for_update().get(pk=order.funnel.owner_id)
        owner.main_balance -= locked_order.commission_amount
        owner.save(update_fields=['main_balance'])
        Order.objects.filter(pk=order.pk).update(commission_paid=False, commission_amount=0)
    order.commission_paid = False
    order.commission_amount = 0


def apply_order_status_effects(order, new_status):
    """Buyurtma statusi o'zgarganda zaxira va komissiya effektlarini qo'llaydi.
    `order.status` hali ESKI holatda bo'lganda chaqirilishi kerak."""
    old_status = order.status

    if new_status == Order.Status.DELIVERED and old_status != Order.Status.DELIVERED:
        credit_commission(order)
    elif old_status == Order.Status.DELIVERED and new_status in (
        Order.Status.RETURNED, Order.Status.CANCELED,
    ):
        reverse_commission(order)

    if new_status in (Order.Status.RETURNED, Order.Status.CANCELED) and old_status not in (
        Order.Status.RETURNED, Order.Status.CANCELED,
    ):
        release_stock(order)
