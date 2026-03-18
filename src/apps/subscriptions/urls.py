from django.urls import path

from .views import (
    CenterRegistrationView,
    CenterSubscriptionView,
    PublicPlanListView,
    SubscriptionStatusView,
    SuperadminInvoiceListView,
    SuperadminInvoiceMarkPaidView,
    SuperadminInvoiceMarkUnpaidView,
    SuperadminSubscriptionListView,
)

# Public (no auth)
public_patterns = [
    path('plans/', PublicPlanListView.as_view(), name='public-plans'),
    path(
        'register-center/',
        CenterRegistrationView.as_view(),
        name='register-center',
    ),
]

# Center admin (auth required)
center_patterns = [
    path(
        'my-subscription/',
        CenterSubscriptionView.as_view(),
        name='center-subscription',
    ),
    path(
        'status/',
        SubscriptionStatusView.as_view(),
        name='subscription-status',
    ),
]

# Superadmin
superadmin_patterns = [
    path(
        'subscriptions/',
        SuperadminSubscriptionListView.as_view(),
        name='sa-subscriptions',
    ),
    path(
        'invoices/',
        SuperadminInvoiceListView.as_view(),
        name='sa-invoices',
    ),
    path(
        'invoices/<int:invoice_id>/mark-paid/',
        SuperadminInvoiceMarkPaidView.as_view(),
        name='sa-invoice-mark-paid',
    ),
    path(
        'invoices/<int:invoice_id>/mark-unpaid/',
        SuperadminInvoiceMarkUnpaidView.as_view(),
        name='sa-invoice-mark-unpaid',
    ),
]

urlpatterns = public_patterns + center_patterns + superadmin_patterns
