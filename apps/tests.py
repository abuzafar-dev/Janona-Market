from django.test import TestCase, Client

from apps.models import Funnel, Order, Product, User, Withdrawal


class FunnelDiscountTests(TestCase):
    """Hamkor chegirmasi narxni 0 ga tushira olmasligi yoki oshira olmasligi kerak."""

    def setUp(self):
        self.product = Product.objects.create(title="Phone", price=1_000_000)
        self.affiliate = User.objects.create_user("998900000001", "Pw-123456")
        self.client = Client()
        self.client.force_login(self.affiliate)

    def create_funnel(self, discount):
        return self.client.post("/admin_page/market/", {
            "product_id": self.product.id, "title": "oqim", "discount": discount,
        })

    def order_via(self, funnel, quantity=1):
        Client().post(f"/funnel/{funnel.id}/", {
            "full_name": "Ali", "phone_number": "998901112233", "quantity": quantity,
        })
        return Order.objects.filter(funnel=funnel).latest("id")

    def test_valid_discount_applied(self):
        self.create_funnel("100000")
        funnel = Funnel.objects.get()
        self.assertEqual(funnel.discount_price, 100_000)
        self.assertEqual(self.order_via(funnel, quantity=2).total_price, 1_800_000)

    def test_no_discount(self):
        self.create_funnel("")
        funnel = Funnel.objects.get()
        self.assertIsNone(funnel.discount_price)
        self.assertEqual(self.order_via(funnel).total_price, 1_000_000)

    def test_rejects_discount_equal_or_above_price(self):
        for value in ("1000000", "5000000"):
            self.create_funnel(value)
        self.assertFalse(Funnel.objects.exists())

    def test_rejects_negative_discount(self):
        self.create_funnel("-5000000")
        self.assertFalse(Funnel.objects.exists())

    def test_rejects_non_numeric_discount_without_500(self):
        response = self.create_funnel("abc")
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Funnel.objects.exists())

    def test_legacy_bad_funnel_does_not_change_price(self):
        # Tuzatishdan oldin yaratilgan noto'g'ri funnellar
        for bad in (-5_000_000, 1_000_000, 2_000_000):
            funnel = Funnel.objects.create(title="eski", slug=f"eski{bad}", product=self.product,
                                           owner=self.affiliate, discount_price=bad)
            self.assertEqual(self.order_via(funnel).total_price, 1_000_000)


class WithdrawalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("998900000001", "Pw-123456")
        self.user.main_balance = 500
        self.user.coins = 70
        self.user.save()
        self.client = Client()
        self.client.force_login(self.user)

    def withdraw(self, **extra):
        data = {"card_number": "8600 1234 1234 1234", "amount": 200, **extra}
        return self.client.post("/admin_page/withdraw/", data)

    def test_ui_form_without_type_creates_money_withdrawal(self):
        self.withdraw()
        self.user.refresh_from_db()
        withdrawal = Withdrawal.objects.get()
        self.assertEqual((withdrawal.type, withdrawal.amount), (Withdrawal.Type.MONEY, 200))
        self.assertEqual((self.user.main_balance, self.user.pending_balance), (300, 200))

    def test_coin_type_does_not_touch_coins_and_is_money(self):
        self.withdraw(type="coin")
        self.user.refresh_from_db()
        self.assertEqual(self.user.coins, 70)
        self.assertEqual(Withdrawal.objects.get().type, Withdrawal.Type.MONEY)

    def test_cannot_withdraw_more_than_balance(self):
        self.withdraw(amount=501)
        self.user.refresh_from_db()
        self.assertFalse(Withdrawal.objects.exists())
        self.assertEqual(self.user.main_balance, 500)

    def admin_action(self, action):
        from django.contrib import admin as django_admin
        from apps.admin import WithdrawalAdmin
        getattr(WithdrawalAdmin(Withdrawal, django_admin.site), action)(None, Withdrawal.objects.all())

    def test_reject_restores_balance_once(self):
        self.withdraw(amount=200)
        self.withdraw(amount=100)
        self.admin_action("mark_rejected")
        self.admin_action("mark_rejected")  # ikkinchi marta bosilsa ham o'zgarmaydi
        self.user.refresh_from_db()
        self.assertEqual((self.user.main_balance, self.user.pending_balance), (500, 0))

    def test_complete_clears_pending_once(self):
        self.withdraw(amount=200)
        self.admin_action("mark_completed")
        self.admin_action("mark_rejected")  # bajarilgan so'rovni rad etib bo'lmaydi
        self.user.refresh_from_db()
        self.assertEqual((self.user.main_balance, self.user.pending_balance), (300, 0))


class AccountSecurityTests(TestCase):
    STRONG = "Murakkab-Parol-2026"

    def register(self, client=None, password=None, **extra):
        password = password or self.STRONG
        return (client or Client()).post("/register/", {
            "phone_number": "998901234567", "password": password, "conf_password": password, **extra,
        })

    def test_weak_passwords_rejected(self):
        for weak in ("abc", "12345678", "password"):
            self.register(password=weak)
        self.assertFalse(User.objects.exists())

    def test_strong_password_registers(self):
        self.register()
        self.assertTrue(User.objects.filter(phone_number="998901234567").exists())

    def test_invalid_ref_id_does_not_crash(self):
        for bad in ("x", "-1", "999999"):
            response = self.register(ref_id=bad)
            self.assertEqual(response.status_code, 302, bad)
            User.objects.all().delete()

    def test_referral_link_records_referrer(self):
        referrer = User.objects.create_user("998900000009", self.STRONG)
        client = Client()
        client.get(f"/register/?id={referrer.id}")  # referal havola ochildi
        self.register(client=client)              # keyin bosh sahifadagi modal yuborildi
        self.assertEqual(User.objects.get(phone_number="998901234567").referred_by, referrer)

    def test_referral_link_has_no_redirect_hop(self):
        user = User.objects.create_user("998900000009", self.STRONG)
        client = Client()
        client.force_login(user)
        link = client.get("/profile/referral/").context["referral_link"]
        self.assertIn("/register/?id=", link)

    def password_change(self, client, current, new, confirm=None):
        return client.post("/profile/settings/", {
            "_password_change": "1", "current_password": current,
            "new_password": new, "confirm_password": confirm or new,
        })

    def test_password_change_requires_current_password(self):
        user = User.objects.create_user("998900000001", self.STRONG)
        client = Client()
        client.force_login(user)
        self.password_change(client, "noto'g'ri", "Yangi-Parol-2027")
        user.refresh_from_db()
        self.assertTrue(user.check_password(self.STRONG))

    def test_password_change_rejects_weak_new_password(self):
        user = User.objects.create_user("998900000001", self.STRONG)
        client = Client()
        client.force_login(user)
        self.password_change(client, self.STRONG, "123456")
        user.refresh_from_db()
        self.assertTrue(user.check_password(self.STRONG))

    def test_password_change_works(self):
        user = User.objects.create_user("998900000001", self.STRONG)
        client = Client()
        client.force_login(user)
        self.password_change(client, self.STRONG, "Yangi-Parol-2027")
        user.refresh_from_db()
        self.assertTrue(user.check_password("Yangi-Parol-2027"))

    def test_logout_is_post_only(self):
        user = User.objects.create_user("998900000001", self.STRONG)
        client = Client()
        client.force_login(user)
        self.assertEqual(client.get("/logout/").status_code, 405)
        self.assertIn("_auth_user_id", client.session)
        client.post("/logout/")
        self.assertNotIn("_auth_user_id", client.session)


class ProductionSettingsTests(TestCase):
    def test_refuses_known_secret_key_when_not_debug(self):
        import os
        import subprocess
        import sys
        from pathlib import Path
        env = {**os.environ, "DEBUG": "False", "SECRET_KEY": "django-insecure-change-me-in-.env",
               "DJANGO_SETTINGS_MODULE": "root.settings"}
        result = subprocess.run([sys.executable, "-c", "import django; django.setup()"],
                                cwd=Path(__file__).resolve().parent.parent, env=env,
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ImproperlyConfigured", result.stderr)


class LogoutTemplateTests(TestCase):
    def test_logout_links_submit_post_form(self):
        user = User.objects.create_user("998900000001", "Murakkab-Parol-2026", is_operator=True)
        client = Client()
        client.force_login(user)
        for url in ("/admin_page/", "/admin_page/orders/new/", "/admin_page/orders/my/", "/profile/settings/"):
            html = client.get(url).content.decode()
            self.assertIn('<form id="logout-form" action="/logout/" method="post"', html, url)
            self.assertIn("getElementById('logout-form').submit()", html, url)
            self.assertNotIn('href="/logout/"', html, url)
            self.assertNotIn("/profile/logout", html, url)
