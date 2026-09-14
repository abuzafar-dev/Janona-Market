import uuid

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import transaction

from django.http import JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.template.defaultfilters import slugify
from django.utils.decorators import method_decorator
from django.views import View

from apps.forms import OrderForm, RegisterForm, LoginForm, WithdrawalForm
from apps.models import User, Category, Product, District, Region, Funnel, Competition, Order, CompetitionResult, \
    Withdrawal, Survey
from django.contrib import messages

from django.db.models import Count, Q
from django.core.paginator import Paginator
from functools import wraps


def operator_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_operator:
            messages.error(request, "Bu yerga faqat operatorlar kirava oladilar!")
            return redirect('home')
        return view_func(request, *args, **kwargs)

    return wrapper
from django import template

register = template.Library()


@register.filter
def space_number(value):
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        return value
    return '{:,}'.format(n).replace(',', ' ')


@register.filter
def format_phone(value):
    if not value:
        return ''
    digits = ''.join(ch for ch in str(value) if ch.isdigit())
    if digits.startswith('998') and len(digits) == 12:
        return '+998 {} {} {} {}'.format(digits[3:5], digits[5:8], digits[8:10], digits[10:12])
    return value


@register.filter
def initials(user):
    if not user:
        return ''
    first = (user.first_name or '').strip()
    last = (user.last_name or '').strip()
    if first or last:
        return (first[:1] + last[:1]).upper()
    phone = (user.phone_number or '')
    digits = ''.join(ch for ch in phone if ch.isdigit())
    return digits[-2:] if digits else '??'

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


class LoginView(View):
    def post(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            phone = clean_phone_number(form.cleaned_data['phone_number'])

            user = authenticate(
                request,
                phone_number=phone,
                password=form.cleaned_data['password'],
            )
            if user is not None:
                login(request, user)
                if user.is_operator:
                    return redirect('new-orders')
                elif user.is_staff or user.is_superuser:
                    return redirect('dashboard')
                else:
                    return redirect('profile-settings')

            messages.error(request, "Telefon raqam yoki parol xato.", extra_tags='login_modal')
            return redirect('home')
        else:
            messages.error(request, "Telefon raqam yoki parol xato.", extra_tags='login_modal')
            return redirect('home')

    def get(self, request):
        return redirect('home')

class RegisterView(View):
    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            phone = clean_phone_number(form.cleaned_data['phone_number'])

            if User.objects.filter(phone_number=phone).exists():
                messages.error(request, "Bu telefon raqam allaqachon ro'yxatdan o'tgan!")
                return redirect('home')

            ref_id = request.POST.get('ref_id') or request.GET.get('id')
            referred_by = User.objects.filter(id=ref_id).first() if ref_id else None

            user = User.objects.create_user(
                phone_number=phone,
                password=form.cleaned_data['password'],
                referred_by=referred_by,
            )
            login(request, user)
            return redirect('profile-settings')

        for field_errors in form.errors.values():
            for error in field_errors:
                messages.error(request, error)
        return redirect('home')

    def get(self, request):
        return redirect('home')


class SearchProductView(View):
    def get(self, request):
        query = request.GET.get('product', '')

        if query:
            products_list = Product.objects.filter(title__icontains=query).order_by('-id')
        else:
            products_list = Product.objects.none()

        paginator = Paginator(products_list, 18)
        page_number = request.GET.get('page')
        products = paginator.get_page(page_number)

        context = {
            'products': products,
            'query': query,
            'categories': Category.objects.all()
        }
        return render(request, 'bosh-sahifa.html', context)

    def post(self, request):
        query = request.POST.get('product', '')
        return redirect(f"{request.path}?product={query}")


class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('home')


class HomeView(View):
    def get(self, request):
        categories = Category.objects.all()
        products = Product.objects.all().order_by('-id')

        context = {
            'categories': categories,
            'products': products,
        }
        return render(request, 'bosh-sahifa.html', context)


class ShopView(View):
    def get(self, request):
        categories = Category.objects.all()
        products_list = Product.objects.all().order_by('-id')
        paginator = Paginator(products_list, 18)
        page_number = request.GET.get('page')
        products = paginator.get_page(page_number)

        context = {
            'categories': categories,
            'products': products,
            'category': None,
        }
        return render(request, 'category.html', context)


class CategoryDetailView(View):
    def get(self, request, slug):
        categories = Category.objects.all().order_by('-id')
        category = get_object_or_404(Category, slug=slug)

        products_list = Product.objects.filter(category=category).order_by('-id')

        paginator = Paginator(products_list, 18)
        page_number = request.GET.get('page')
        products = paginator.get_page(page_number)

        context = {
            'categories': categories,
            'category': category,
            'products': products,
        }
        return render(request, 'category.html', context)


class ProductDetailView(View):
    def get(self, request, slug):
        product = get_object_or_404(Product, slug=slug)
        context = {
            'product': product,
            'categories': Category.objects.all(),
        }
        return render(request, 'product-detail.html', context)

    def post(self, request, slug):
        product = get_object_or_404(Product, slug=slug)
        form = OrderForm(request.POST)

        if form.is_valid():
            order = form.save(commit=False)
            order.product = product
            order.phone_number = clean_phone_number(form.cleaned_data['phone_number'])
            order.total_price = product.price * order.quantity
            order.user = request.user if request.user.is_authenticated else None
            order.save()
            messages.success(request, "Buyurtmangiz muvaffaqiyatli qabul qilindi!")
        else:
            messages.error(request, "Ma'lumotlarni to'g'ri kiriting: " + form.errors.as_text())

        return redirect('product-detail', slug=product.slug)


@method_decorator(login_required, name='dispatch')
class ProfileSettingsView(View):
    def get(self, request):
        context = {
            'regions': Region.objects.all().order_by('title'),
            'districts': District.objects.filter(
                region=request.user.region
            ).order_by('title') if request.user.region_id else District.objects.none(),
        }
        return render(request, 'settings.html', context)

    def post(self, request):
        user = request.user

        if request.POST.get('_password_change'):
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')

            if not new_password or len(new_password) < 6:
                messages.error(request, "Parol kamida 6 belgidan iborat bo'lishi kerak.")
            elif new_password != confirm_password:
                messages.error(request, "Parollar mos tushmadi.")
            else:
                user.set_password(new_password)
                user.save()
                messages.success(request, "Parol muvaffaqiyatli o'zgartirildi. Qayta kiring.")
                return redirect('home')

            return redirect('profile-settings')

        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name = request.POST.get('last_name', '').strip()
        user.telegram_id = request.POST.get('telegram_id', '').strip()
        user.bio = request.POST.get('description', '').strip()

        region_id = request.POST.get('region')
        if region_id and Region.objects.filter(id=region_id).exists():
            user.region_id = region_id
        else:
            user.region_id = None
            user.district = None

        district_name = request.POST.get('city')
        if district_name and user.region_id:
            district = District.objects.filter(
                title=district_name, region_id=user.region_id
            ).first()
            user.district = district
        elif not district_name:
            user.district = None

        user.save()
        messages.success(request, "Profil ma'lumotlari saqlandi.")
        return redirect('profile-settings')


def get_districts(request, region_id):
    districts = District.objects.filter(region_id=region_id).order_by('title').values('title')
    data = [{'name': d['title']} for d in districts]
    return JsonResponse({'districts': data})


@method_decorator(login_required, name='dispatch')
class MarketView(View):
    def get(self, request, category_slug=None):
        categories = Category.objects.all()
        products_list = Product.objects.all().order_by('-id')
        selected_category = None
        if category_slug:
            selected_category = get_object_or_404(Category, slug=category_slug)
            products_list = products_list.filter(category=selected_category)
        search_query = request.GET.get('q', '')
        if search_query:
            products_list = products_list.filter(title__icontains=search_query)
        paginator = Paginator(products_list, 9)
        page_number = request.GET.get('page')
        products = paginator.get_page(page_number)
        context = {
            'categories': categories,
            'products': products,
            'selected_category': selected_category,
            'search_query': search_query,
        }
        return render(request, 'market.html', context)

    def post(self, request, category_slug=None):
        product_id = request.POST.get('product_id')
        title = request.POST.get('title', '').strip()
        discount = request.POST.get('discount') or None

        if not product_id:
            messages.error(request, "Mahsulot tanlanmagan.")
            return redirect(request.path)

        product = get_object_or_404(Product, id=product_id)

        if not title:
            messages.error(request, "Oqim nomini kiriting.")
            return redirect(request.path)

        base_slug = slugify(title) or 'oqim'
        slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
        while Funnel.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"

        Funnel.objects.create(
            title=title,
            slug=slug,
            product=product,
            owner=request.user,
            discount_price=discount,
        )
        messages.success(request, f"'{title}' oqimi muvaffaqiyatli yaratildi!")
        return redirect('links')


class FunnelDetailView(View):
    def get(self, request, funnel_id):
        funnel = get_object_or_404(Funnel, id=funnel_id, is_active=True)
        context = {
            'funnel': funnel,
            'product': funnel.product,
            'categories': Category.objects.all(),
        }
        return render(request, 'product-detail.html', context)

    def post(self, request, funnel_id):
        funnel = get_object_or_404(Funnel, id=funnel_id, is_active=True)
        product = funnel.product
        form = OrderForm(request.POST)

        if form.is_valid():
            order = form.save(commit=False)
            order.product = product
            order.funnel = funnel
            order.phone_number = clean_phone_number(form.cleaned_data['phone_number'])

            price = product.price
            if funnel.discount_price:
                price = max(price - funnel.discount_price, 0)
            order.total_price = price * order.quantity

            order.user = request.user if request.user.is_authenticated else None
            order.save()
            messages.success(request, "Buyurtmangiz muvaffaqiyatli qabul qilindi!")
        else:
            messages.error(request, "Ma'lumotlarni to'g'ri kiriting: " + form.errors.as_text())

        return redirect('funnel-detail', funnel_id=funnel.id)


@method_decorator(login_required, name='dispatch')
class DashboardView(View):
    def get(self, request):
        return render(request, 'dashboard.html')


@method_decorator(login_required, name='dispatch')
class StatisticView(View):
    def get(self, request):
        funnels_list = Funnel.objects.filter(owner=request.user).annotate(
            new_num=Count('orders', filter=Q(orders__status='new')),
            packing_num=Count('orders', filter=Q(orders__status='packing')),
            later_num=Count('orders', filter=Q(orders__status='later')),
            returned_num=Count('orders', filter=Q(orders__status='returned')),
            cancelled_num=Count('orders', filter=Q(orders__status='cancelled')),
            hold_num=Count('orders', filter=Q(orders__status='hold')),
            archive_num=Count('orders', filter=Q(orders__status='archive')),
            delivering_num=Count('orders', filter=Q(orders__status='delivering')),
            delivered_num=Count('orders', filter=Q(orders__status='delivered')),
        ).order_by('-created_at')
        paginator = Paginator(funnels_list, 10)
        page_number = request.GET.get('page')
        funnels = paginator.get_page(page_number)

        context = {
            'funnels': funnels,
        }
        return render(request, 'statistic.html', context)


@method_decorator(login_required, name='dispatch')
class LinksView(View):
    def get(self, request):
        query = request.GET.get('q', '').strip()
        links_list = Funnel.objects.filter(owner=request.user).order_by('-created_at')

        if query:
            if query.isdigit():
                links_list = links_list.filter(id=query)
            else:
                links_list = links_list.filter(title__icontains=query)

        paginator = Paginator(links_list, 6)
        page_number = request.GET.get('page')
        links = paginator.get_page(page_number)

        context = {
            'links': links,
            'query': query,
        }
        return render(request, 'links.html', context)


@method_decorator(login_required, name='dispatch')
class DeleteLinkView(View):
    def post(self, request, link_id):
        funnel = get_object_or_404(Funnel, id=link_id, owner=request.user)
        funnel.delete()
        return JsonResponse({'success': True})


class CompetitionView(View):
    RESULTS_CACHE_TTL = 60 * 60 * 12  # 12 soat

    def get(self, request):
        competition = Competition.objects.filter(is_active=True).order_by('-start_date').first()
        results = []

        if competition:
            cache_key = f"competition:{competition.pk}:results"
            results = cache.get(cache_key)

            if results is None:
                results = list(
                    competition.results
                    .order_by('-sold_count')
                    .values('display_name', 'sold_count')
                )
                cache.set(cache_key, results, self.RESULTS_CACHE_TTL)

        context = {
            'competition': competition,
            'results': results,
        }
        return render(request, 'contest.html', context)


@method_decorator(login_required, name='dispatch')
class BalanceView(View):
    def get(self, request):
        withdrawals_list = request.user.withdrawals.order_by('-created_at')
        paginator = Paginator(withdrawals_list, 10)
        page_number = request.GET.get('page')
        withdrawals = paginator.get_page(page_number)

        context = {
            'balance': request.user.main_balance,
            'pending_balance': request.user.pending_balance,
            'withdrawals': withdrawals,
        }
        return render(request, 'balance.html', context)

    def post(self, request):
        form = WithdrawalForm(request.POST, user=request.user)

        if form.is_valid():
            with transaction.atomic():
                user = User.objects.select_for_update().get(pk=request.user.pk)
                amount = form.cleaned_data['amount']

                if amount > user.main_balance:
                    messages.error(request, "Hisobingizdagi mavjud summadan ko'p miqdor kiritdingiz.")
                    return redirect('balance')

                withdrawal = form.save(commit=False)
                withdrawal.user = user
                withdrawal.status = Withdrawal.Status.PENDING
                withdrawal.save()

                user.main_balance -= amount
                user.pending_balance += amount
                user.save(update_fields=['main_balance', 'pending_balance'])

            messages.success(request, "So'rovingiz qabul qilindi. Operator tez orada ko'rib chiqadi.")
        else:
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)

        return redirect('balance')


@method_decorator(login_required, name='dispatch')
class ReferralView(View):
    def get(self, request):
        referrals_list = request.user.referrals.order_by('-created_at')
        paginator = Paginator(referrals_list, 10)
        page_number = request.GET.get('page')
        referrals = paginator.get_page(page_number)

        context = {
            'referral_link': request.build_absolute_uri('/register') + f'?id={request.user.id}',
            'referral_count': referrals_list.count(),
            'referrals': referrals,
        }
        return render(request, 'referral.html', context)


class SurveyView(View):
    @method_decorator(login_required)
    def get(self, request):
        query = request.GET.get('q', '').strip()
        status_filter = request.GET.get('status', '').strip()

        surveys_list = Survey.objects.filter(
            funnel__owner=request.user
        ).select_related('operator', 'funnel', 'region').order_by('-created_at')

        if query:
            if query.isdigit():
                surveys_list = surveys_list.filter(id=query)
            else:
                surveys_list = surveys_list.filter(
                    Q(buyer_name__icontains=query) | Q(phone_number__icontains=query)
                )

        if status_filter:
            surveys_list = surveys_list.filter(status=status_filter)

        paginator = Paginator(surveys_list, 10)
        page_number = request.GET.get('page')
        surveys = paginator.get_page(page_number)

        context = {
            'surveys': surveys,
            'query': query,
            'status_filter': status_filter,
            'status_choices': Survey.Status.choices,
        }
        return render(request, 'questionnaire.html', context)


# ------------------------------------------------------------------
# OPERATOR PANELI: my-orders.html, new-orders.html, order-detail.html
# ------------------------------------------------------------------
class OperatorRequiredMixin:
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_operator:
            messages.error(request, "Sizda operator panelidan foydalanish huquqi yo'q.")
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)


STATUS_MAP = {
    'packaging': Order.Status.PACKING,
    'shipping': Order.Status.DELIVERING,
    'delivered': Order.Status.DELIVERED,
    'pickup_later': Order.Status.LATER,
    'hold': Order.Status.HOLD,
    'returned': Order.Status.RETURNED,
    'cancelled': Order.Status.CANCELED,
    'archive': Order.Status.ARCHIVE,
}

SURVEY_STATUS_MAP = {
    'packaging': Survey.Status.PROCESSING,
    'shipping': Survey.Status.PROCESSING,
    'delivered': Survey.Status.CONFIRMED,
    'pickup_later': Survey.Status.PROCESSING,
    'hold': Survey.Status.PROCESSING,
    'returned': Survey.Status.REJECTED,
    'cancelled': Survey.Status.REJECTED,
    'archive': Survey.Status.PROCESSING,
}


def _log_survey(order, operator, ui_status, comment):
    if not order.funnel_id:
        return
    Survey.objects.create(
        operator=operator,
        funnel=order.funnel,
        buyer_name=order.full_name,
        region=order.region,
        phone_number=order.phone_number,
        status=SURVEY_STATUS_MAP.get(ui_status, Survey.Status.PROCESSING),
        comment=comment,
    )


@method_decorator(login_required, name='dispatch')
class NewOrdersView(OperatorRequiredMixin, View):

    def get(self, request):
        pool = Order.objects.filter(
            status=Order.Status.NEW, operator__isnull=True
        ).select_related('product', 'product__category', 'funnel', 'region').order_by('-created_at')

        context = {
            'orders': pool,
            'regions': Region.objects.all().order_by('title'),
            'new_orders_count': pool.count(),
            'my_orders_count': Order.objects.filter(operator=request.user).count(),
        }
        return render(request, 'new-orders.html', context)

@method_decorator(login_required, name='dispatch')
class TakeOrderView(OperatorRequiredMixin, View):

    def post(self, request, order_id):
        updated = Order.objects.filter(
            pk=order_id, status=Order.Status.NEW, operator__isnull=True,
        ).update(operator=request.user)

        if updated:
            return JsonResponse({'success': True})
        return JsonResponse(
            {'success': False, 'message': "Bu buyurtmani boshqa operator allaqachon oldi."},
            status=409,
        )


@method_decorator(login_required, name='dispatch')
class MyOrdersView(OperatorRequiredMixin, View):

    def get(self, request):
        orders = Order.objects.filter(
            operator=request.user
        ).select_related('product', 'funnel', 'region').order_by('-created_at')

        context = {
            'orders': orders,
            'regions': Region.objects.all().order_by('title'),
            'my_orders_count': orders.count(),
            'new_orders_count': Order.objects.filter(
                status=Order.Status.NEW, operator__isnull=True
            ).count(),
        }
        return render(request, 'my-orders.html', context)


@method_decorator(login_required, name='dispatch')
class OrderQuickStatusView(OperatorRequiredMixin, View):

    def post(self, request, order_id):
        order = get_object_or_404(Order, pk=order_id, operator=request.user)

        ui_status = request.POST.get('status')
        comment = request.POST.get('comment', '').strip()

        if ui_status not in STATUS_MAP:
            messages.error(request, "Holat noto'g'ri tanlandi.")
            return redirect('my-orders')

        order.status = STATUS_MAP[ui_status]
        order.save(update_fields=['status', 'updated_at'])

        _log_survey(order, request.user, ui_status, comment)

        messages.success(request, f"Buyurtma #{order.id} holati yangilandi.")
        return redirect('my-orders')


@method_decorator(login_required, name='dispatch')
class OrderDetailView(OperatorRequiredMixin, View):
    def get(self, request, order_id):
        order = get_object_or_404(
            Order.objects.select_related('product', 'funnel', 'region', 'district'),
            pk=order_id, operator=request.user,
        )

        previous_orders = Order.objects.filter(
            phone_number=order.phone_number
        ).exclude(pk=order.pk).select_related('product').order_by('-created_at')[:10]

        regions = Region.objects.all().order_by('title')
        # {{ districts_map|json_script:"op-regions-data" }} qilib shablonga
        # qo'ying, JS window.OP_REGIONS shundan o'qiydi (kommentda aytilgani kabi).
        districts_map = {
            region.id: list(region.districts.order_by('title').values_list('id', 'title'))
            for region in regions
        }

        context = {
            'order': order,
            'previous_orders': previous_orders,
            'regions': regions,
            'districts_map': districts_map,
        }
        return render(request, 'order-detail.html', context)

    def post(self, request, order_id):
        order = get_object_or_404(Order, pk=order_id, operator=request.user)

        ui_status = request.POST.get('status')
        if ui_status not in STATUS_MAP:
            messages.error(request, "Buyurtma holatini tanlang.")
            return redirect('order-detail', order_id=order.id)

        order.full_name = request.POST.get('customer_name', '').strip() or order.full_name
        order.phone_number = clean_phone_number(request.POST.get('phone', '')) or order.phone_number
        order.region_id = request.POST.get('region') or None
        order.district_id = request.POST.get('district') or None
        order.shipping_address = request.POST.get('address', '').strip()

        try:
            quantity = max(int(request.POST.get('quantity', order.quantity)), 1)
        except (TypeError, ValueError):
            quantity = order.quantity
        order.quantity = quantity

        if order.product:
            price = order.product.price
            if order.funnel and order.funnel.discount_price:
                price = max(price - order.funnel.discount_price, 0)
            order.total_price = price * quantity

        order.status = STATUS_MAP[ui_status]
        order.save()

        comment = request.POST.get('comment', '').strip()
        _log_survey(order, request.user, ui_status, comment)

        messages.success(request, f"Buyurtma #{order.id} saqlandi.")
        return redirect('my-orders')
