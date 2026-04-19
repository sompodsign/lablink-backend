from django.urls import path

from .subscription_gateway_views import (
    SubscriptionInitiateChargeView,
)
from .subscription_gateway_views import (
    SubscriptionVerifyPaymentView as GatewayVerifyView,
)
from .views import (
    CenterAvailablePlansView,
    CenterCancelSubscriptionView,
    CenterChangePlanView,
    CenterInvoiceListView,
    CenterRegistrationView,
    CenterResumeSubscriptionView,
    CenterSubmitPaymentView,
    CenterSubscriptionView,
    PaymentInfoListView,
    PublicPlanListView,
    SubscriptionStatusView,
    SuperadminChangePlanView,
    SuperadminCreateInvoiceView,
    SuperadminExtendTrialView,
    SuperadminInvoiceListView,
    SuperadminInvoiceMarkPaidView,
    SuperadminInvoiceMarkUnpaidView,
    SuperadminInvoiceCancelView,
    SuperadminPaymentSubmissionListView,
    SuperadminSubscriptionDetailView,
    SuperadminSubscriptionListView,
    SuperadminVerifyPaymentView,
)

# Public (no auth)
public_patterns = [
    path("plans/", PublicPlanListView.as_view(), name="public-plans"),
    path(
        "payment-info/",
        PaymentInfoListView.as_view(),
        name="payment-info",
    ),
    path(
        "register-center/",
        CenterRegistrationView.as_view(),
        name="register-center",
    ),
]

# Center admin (auth required)
center_patterns = [
    path(
        "available-plans/",
        CenterAvailablePlansView.as_view(),
        name="center-available-plans",
    ),
    path(
        "my-subscription/",
        CenterSubscriptionView.as_view(),
        name="center-subscription",
    ),
    path(
        "my-subscription/change-plan/",
        CenterChangePlanView.as_view(),
        name="center-change-plan",
    ),
    path(
        "my-subscription/cancel/",
        CenterCancelSubscriptionView.as_view(),
        name="center-cancel-subscription",
    ),
    path(
        "my-subscription/resume/",
        CenterResumeSubscriptionView.as_view(),
        name="center-resume-subscription",
    ),
    path(
        "status/",
        SubscriptionStatusView.as_view(),
        name="subscription-status",
    ),
    path(
        "my-invoices/",
        CenterInvoiceListView.as_view(),
        name="center-invoices",
    ),
    path(
        "invoices/<int:invoice_id>/submit-payment/",
        CenterSubmitPaymentView.as_view(),
        name="center-submit-payment",
    ),
    # UddoktaPay gateway for subscription payments
    path(
        "gateway/initiate-charge/",
        SubscriptionInitiateChargeView.as_view(),
        name="subscription-gateway-initiate",
    ),
    path(
        "gateway/verify-payment/",
        GatewayVerifyView.as_view(),
        name="subscription-gateway-verify",
    ),
]

# Superadmin
superadmin_patterns = [
    path(
        "subscriptions/",
        SuperadminSubscriptionListView.as_view(),
        name="sa-subscriptions",
    ),
    path(
        "subscriptions/<int:subscription_id>/",
        SuperadminSubscriptionDetailView.as_view(),
        name="sa-subscription-detail",
    ),
    path(
        "invoices/",
        SuperadminInvoiceListView.as_view(),
        name="sa-invoices",
    ),
    path(
        "invoices/<int:invoice_id>/mark-paid/",
        SuperadminInvoiceMarkPaidView.as_view(),
        name="sa-invoice-mark-paid",
    ),
    path(
        "invoices/<int:invoice_id>/mark-unpaid/",
        SuperadminInvoiceMarkUnpaidView.as_view(),
        name="sa-invoice-mark-unpaid",
    ),
    path(
        "invoices/<int:invoice_id>/cancel/",
        SuperadminInvoiceCancelView.as_view(),
        name="sa-invoice-cancel",
    ),
    path(
        "subscriptions/<int:subscription_id>/extend-trial/",
        SuperadminExtendTrialView.as_view(),
        name="sa-extend-trial",
    ),
    path(
        "subscriptions/<int:subscription_id>/change-plan/",
        SuperadminChangePlanView.as_view(),
        name="sa-change-plan",
    ),
    path(
        "subscriptions/<int:subscription_id>/create-invoice/",
        SuperadminCreateInvoiceView.as_view(),
        name="sa-create-invoice",
    ),
    path(
        "payment-submissions/",
        SuperadminPaymentSubmissionListView.as_view(),
        name="sa-payment-submissions",
    ),
    path(
        "payment-submissions/<int:submission_id>/review/",
        SuperadminVerifyPaymentView.as_view(),
        name="sa-verify-payment",
    ),
]

urlpatterns = public_patterns + center_patterns + superadmin_patterns
