from django.urls import path
from .views import merchant_dashboard, create_payout

urlpatterns = [
    path('merchants/me', merchant_dashboard, name='merchant_dashboard'),
    path('payouts', create_payout, name='create_payout'),
]
