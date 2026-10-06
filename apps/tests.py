from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import TestCase, Client, RequestFactory
from django.urls import reverse

from apps.admin import WithdrawalAdmin
from apps.forms import RegisterForm, WithdrawalForm
from apps.models import Funnel, Order, Product, User, Withdrawal


def create_user(phone_number, **kwargs):
    return User.objects.create_user(phone_number=phone_number, password='testpass123', **kwargs)


def admin_request():
    """message_user() needs a real request carrying a messages storage."""
    request = RequestFactory().get('/admin/')
    request.session = {}
    request._messages = FallbackStorage(request)
    return request


_product_counter = 0


def create_product(**kwargs):
    global _product_counter
    _product_counter += 1
    defaults = {
        'title': f'Test mahsulot {_product_counter}',
        'price': 100000,
        'stock_quantity': 10,
    }
    defaults.update(kwargs)
    return Product.objects.create(**defaults)


class BalanceViewTests(TestCase):
    def setUp(self):
        self.user = create_user('998900000001', main_balance=50000)
        self.client = Client()
        self.client.force_login(self.user)

    def test_successful_withdrawal_moves_balance(self):
        response = self.client.post(reverse('balance'), {
            'card_number': '8600123412341234',
            'amount': '20000',
            'type': Withdrawal.Type.MONEY,
        })
        self.assertRedirects(response, reverse('balance'))

        self.user.refresh_from_db()
        self.assertEqual(self.user.main_balance, 30000)
        self.assertEqual(self.user.pending_balance, 20000)
        self.assertEqual(Withdrawal.objects.count(), 1)
        withdrawal = Withdrawal.objects.first()
        self.assertEqual(withdrawal.status, Withdrawal.Status.PENDING)
        self.assertEqual(withdrawal.amount, 20000)

    def test_insufficient_balance_rejected(self):
        response = self.client.post(reverse('balance'), {
            'card_number': '8600123412341234',
            'amount': '999999',
            'type': Withdrawal.Type.MONEY,
        })
        self.assertRedirects(response, reverse('balance'))

        self.user.refresh_from_db()
        self.assertEqual(self.user.main_balance, 50000)
        self.assertEqual(self.user.pending_balance, 0)
        self.assertEqual(Withdrawal.objects.count(), 0)


class WithdrawalAdminActionTests(TestCase):
    def setUp(self):
        self.user = create_user('998900000002', main_balance=0, pending_balance=30000)
        self.withdrawal = Withdrawal.objects.create(
            user=self.user, card_number='8600123412341234', amount=30000,
            status=Withdrawal.Status.PENDING,
        )
        self.admin = WithdrawalAdmin(Withdrawal, AdminSite())

    def test_mark_completed_moves_pending_to_zero(self):
        qs = Withdrawal.objects.filter(pk=self.withdrawal.pk)
        self.admin.mark_completed(request=admin_request(), queryset=qs)

        self.user.refresh_from_db()
        self.withdrawal.refresh_from_db()
        self.assertEqual(self.user.pending_balance, 0)
        self.assertEqual(self.user.main_balance, 0)
        self.assertEqual(self.withdrawal.status, Withdrawal.Status.COMPLETED)
        self.assertIsNotNone(self.withdrawal.processed_at)

    def test_mark_rejected_returns_money_to_main_balance(self):
        qs = Withdrawal.objects.filter(pk=self.withdrawal.pk)
        self.admin.mark_rejected(request=admin_request(), queryset=qs)

        self.user.refresh_from_db()
        self.withdrawal.refresh_from_db()
        self.assertEqual(self.user.pending_balance, 0)
        self.assertEqual(self.user.main_balance, 30000)
        self.assertEqual(self.withdrawal.status, Withdrawal.Status.REJECTED)

    def test_mark_completed_is_idempotent(self):
        qs = Withdrawal.objects.filter(pk=self.withdrawal.pk)
        self.admin.mark_completed(request=admin_request(), queryset=qs)
        # Same withdrawal (now COMPLETED) run through the action again — the
        # status filter already excludes it, but even a raw re-run must not
        # touch the balance twice.
        self.admin.mark_completed(request=admin_request(), queryset=Withdrawal.objects.filter(pk=self.withdrawal.pk))

        self.user.refresh_from_db()
        self.assertEqual(self.user.pending_balance, 0)
        self.assertEqual(self.user.main_balance, 0)


class CommissionCreditingTests(TestCase):
    def setUp(self):
        self.seller = create_user('998900000003', main_balance=0)
        self.operator = create_user('998900000004', is_operator=True)
        self.product = create_product(stock_quantity=5)
        self.funnel = Funnel.objects.create(
            title='Test oqim', product=self.product, owner=self.seller, commission=15000,
        )
        self.order = Order.objects.create(
            status=Order.Status.NEW, user=None, funnel=self.funnel, product=self.product,
            quantity=2, full_name='Ali Aliyev', phone_number='998901112233',
            total_price=200000, operator=self.operator, stock_deducted=True,
        )
        self.client = Client()
        self.client.force_login(self.operator)

    def test_delivering_order_credits_seller_balance(self):
        response = self.client.post(
            reverse('order-quick-status', args=[self.order.id]),
            {'status': 'delivered', 'comment': ''},
        )
        self.assertRedirects(response, reverse('my-orders'))

        self.seller.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.seller.main_balance, 30000)  # 15000 * 2 dona
        self.assertTrue(self.order.commission_paid)
        self.assertEqual(self.order.commission_amount, 30000)

    def test_commission_not_paid_twice_on_repeated_delivered_status(self):
        self.client.post(reverse('order-quick-status', args=[self.order.id]), {'status': 'delivered'})
        self.client.post(reverse('order-quick-status', args=[self.order.id]), {'status': 'delivered'})

        self.seller.refresh_from_db()
        self.assertEqual(self.seller.main_balance, 30000)

    def test_returning_delivered_order_reverses_commission(self):
        self.client.post(reverse('order-quick-status', args=[self.order.id]), {'status': 'delivered'})
        self.seller.refresh_from_db()
        self.assertEqual(self.seller.main_balance, 30000)

        self.client.post(reverse('order-quick-status', args=[self.order.id]), {'status': 'returned'})
        self.seller.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.seller.main_balance, 0)
        self.assertFalse(self.order.commission_paid)

    def test_no_commission_without_funnel(self):
        order = Order.objects.create(
            status=Order.Status.NEW, funnel=None, product=self.product,
            quantity=1, full_name='Vali Valiyev', phone_number='998901112244',
            total_price=100000, operator=self.operator, stock_deducted=True,
        )
        self.client.post(reverse('order-quick-status', args=[order.id]), {'status': 'delivered'})

        self.seller.refresh_from_db()
        self.assertEqual(self.seller.main_balance, 0)


class StockDecrementTests(TestCase):
    def setUp(self):
        self.product = create_product(stock_quantity=3)
        self.client = Client()

    def test_order_creation_decrements_stock(self):
        response = self.client.post(
            reverse('product-detail', args=[self.product.slug]),
            {'full_name': 'Test User', 'phone_number': '998901234567', 'quantity': 2},
        )
        self.assertRedirects(response, reverse('product-detail', args=[self.product.slug]))

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 1)
        order = Order.objects.get(product=self.product)
        self.assertTrue(order.stock_deducted)

    def test_out_of_stock_order_rejected(self):
        response = self.client.post(
            reverse('product-detail', args=[self.product.slug]),
            {'full_name': 'Test User', 'phone_number': '998901234567', 'quantity': 10},
        )
        self.assertRedirects(response, reverse('product-detail', args=[self.product.slug]))

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 3)
        self.assertEqual(Order.objects.count(), 0)

    def test_stock_never_goes_negative_under_concurrent_orders(self):
        from apps.views import reserve_stock

        product = create_product(stock_quantity=1)
        results = []

        def try_reserve():
            results.append(reserve_stock(product, 1))

        # SQLite + threads sharing one connection would deadlock, so this
        # exercises the same atomic conditional-update codepath sequentially
        # to prove a second reservation is refused once stock hits zero.
        try_reserve()
        try_reserve()

        product.refresh_from_db()
        self.assertEqual(results, [True, False])
        self.assertEqual(product.stock_quantity, 0)


class TakeOrderConcurrencyTests(TestCase):
    def setUp(self):
        self.operator1 = create_user('998900000005', is_operator=True)
        self.operator2 = create_user('998900000006', is_operator=True)
        self.product = create_product()
        self.order = Order.objects.create(
            status=Order.Status.NEW, product=self.product, quantity=1,
            full_name='Test', phone_number='998907654321', total_price=100000,
        )

    def test_second_operator_gets_409(self):
        client1 = Client()
        client1.force_login(self.operator1)
        client2 = Client()
        client2.force_login(self.operator2)

        r1 = client1.post(reverse('order-take', args=[self.order.id]))
        r2 = client2.post(reverse('order-take', args=[self.order.id]))

        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json()['success'], True)
        self.assertEqual(r2.status_code, 409)
        self.assertEqual(r2.json()['success'], False)

        self.order.refresh_from_db()
        self.assertEqual(self.order.operator_id, self.operator1.id)


class FormValidationTests(TestCase):
    def test_withdrawal_card_number_must_be_16_digits(self):
        user = create_user('998900000007', main_balance=100000)
        form = WithdrawalForm(data={'card_number': '1234', 'amount': '10000', 'type': 'money'}, user=user)
        self.assertFalse(form.is_valid())
        self.assertIn('card_number', form.errors)

    def test_withdrawal_amount_must_be_positive(self):
        user = create_user('998900000008', main_balance=100000)
        form = WithdrawalForm(
            data={'card_number': '8600123412341234', 'amount': '0', 'type': 'money'}, user=user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)

    def test_withdrawal_amount_cannot_exceed_balance(self):
        user = create_user('998900000009', main_balance=1000)
        form = WithdrawalForm(
            data={'card_number': '8600123412341234', 'amount': '5000', 'type': 'money'}, user=user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)

    def test_register_form_rejects_password_mismatch(self):
        form = RegisterForm(data={
            'phone_number': '998901112233', 'password': 'secret123', 'conf_password': 'different',
        })
        self.assertFalse(form.is_valid())

    def test_register_form_accepts_matching_passwords(self):
        form = RegisterForm(data={
            'phone_number': '998901112233', 'password': 'secret123', 'conf_password': 'secret123',
        })
        self.assertTrue(form.is_valid())
