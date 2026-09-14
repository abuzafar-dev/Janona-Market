from django.urls import path

from apps.views import (
    LoginView, RegisterView, LogoutView, HomeView, SearchProductView,
    ShopView, CategoryDetailView, ProductDetailView, ProfileSettingsView,
    get_districts, DashboardView, MarketView, LinksView, DeleteLinkView, FunnelDetailView, StatisticView,
    CompetitionView, BalanceView, ReferralView, SurveyView, NewOrdersView, MyOrdersView, TakeOrderView, OrderDetailView,
    OrderQuickStatusView
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('search/', SearchProductView.as_view(), name='search_product'),
    path('category/', ShopView.as_view(), name='shop'),
    path('category/<slug:slug>/', CategoryDetailView.as_view(), name='category_detail'),
    path('product-detail/<slug:slug>/', ProductDetailView.as_view(), name='product-detail'),
    path('profile/settings/', ProfileSettingsView.as_view(), name='profile-settings'),
    path('get-districts/<int:region_id>/', get_districts, name='get-districts'),
    path('admin_page/', DashboardView.as_view(), name='dashboard'),
    path('admin_page/market/', MarketView.as_view(), name='market'),
    path('admin_page/market/<slug:category_slug>/', MarketView.as_view(), name='market_by_category'),
    path('admin_page/links/', LinksView.as_view(), name='links'),
    path('admin_page/links/delete/<int:link_id>/', DeleteLinkView.as_view(), name='delete_link'),
    path('funnel/<int:funnel_id>/', FunnelDetailView.as_view(), name='funnel-detail'),
    path('admin_page/stats/', StatisticView.as_view(), name='stats'),
    path('admin_page/competition/', CompetitionView.as_view(), name='competition'),
    path('admin_page/withdraw/', BalanceView.as_view(), name='balance'),
    path('profile/referral/', ReferralView.as_view(), name='referral'),
    path('admin_page/requests/', SurveyView.as_view(), name='requests'),
    path('admin_page/orders/new/', NewOrdersView.as_view(), name='new-orders'),
    path('admin_page/orders/my/', MyOrdersView.as_view(), name='my-orders'),
    path('admin_page/orders/<int:order_id>/', OrderDetailView.as_view(), name='order-detail'),
    path('admin_page/orders/<int:order_id>/take/', TakeOrderView.as_view(), name='order-take'),
    path('admin_page/orders/<int:order_id>/status/', OrderQuickStatusView.as_view(), name='order-quick-status'),
]
