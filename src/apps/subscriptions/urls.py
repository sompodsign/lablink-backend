from django.urls import path

from .views import (
    CenterCancelSubscriptionView,
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
        "my-subscription/",
        CenterSubscriptionView.as_view(),
        name="center-subscription",
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
