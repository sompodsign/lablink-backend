import contextlib
import logging

from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.emails import EmailType, send_email_async
from core.tenants.permissions import IsCenterAdmin, IsSuperAdmin

from .models import (
    Invoice,
    PaymentInfo,
    PaymentSubmission,
    Subscription,
    SubscriptionPlan,
)
from .serializers import (
    CenterRegistrationSerializer,
    InvoiceSerializer,
    PaymentInfoSerializer,
    PaymentSubmissionSerializer,
    SubmitPaymentSerializer,
    SubscriptionPlanSerializer,
    SubscriptionSerializer,
    SuperadminSubscriptionSerializer,
)

logger = logging.getLogger(__name__)


# ── Public Views ─────────────────────────────────────────────────


class PublicPlanListView(APIView):
    """Public: list available subscription plans."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        plans = SubscriptionPlan.objects.filter(is_active=True)
        serializer = SubscriptionPlanSerializer(plans, many=True)
        return Response(serializer.data)


class PaymentInfoListView(APIView):
    """Public: list active payment methods (bKash, bank, etc.)."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        methods = PaymentInfo.objects.filter(is_active=True)
        serializer = PaymentInfoSerializer(methods, many=True)
        return Response(serializer.data)


class CenterRegistrationView(APIView):
    """Public: register a new diagnostic center with subscription."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = CenterRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        center = result["center"]
        subscription = result["subscription"]

        response_data = {
            "detail": "Center registered successfully!",
            "center": {
                "id": center.id,
                "name": center.name,
                "domain": center.domain,
            },
            "subscription": {
                "plan": subscription.plan.name,
                "status": subscription.status,
                "trial_end": (
                    subscription.trial_end.isoformat()
                    if subscription.trial_end
                    else None
                ),
            },
            "admin": {
                "username": result["admin_user"].username,
                "email": result["admin_user"].email,
            },
        }

        return Response(response_data, status=status.HTTP_201_CREATED)


# ── Center Admin Views ───────────────────────────────────────────


class CenterSubscriptionView(APIView):
    """Center admin: view own subscription details."""

    permission_classes = [permissions.IsAuthenticated, IsCenterAdmin]

    def get(self, request):
        tenant = request.tenant
        if not tenant:
            return Response(
                {"detail": "No center context."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            subscription = Subscription.objects.select_related("plan").get(
                center=tenant,
            )
        except Subscription.DoesNotExist:
            return Response(
                {"detail": "No subscription found for this center."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = SubscriptionSerializer(subscription)
        return Response(serializer.data)


class CenterCancelSubscriptionView(APIView):
    """Center admin: cancel subscription at the end of the current billing cycle."""

    permission_classes = [permissions.IsAuthenticated, IsCenterAdmin]

    def post(self, request):
        tenant = request.tenant
        if not tenant:
            return Response(
                {"detail": "No center context."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            subscription = Subscription.objects.get(center=tenant)
        except Subscription.DoesNotExist:
            return Response(
                {"detail": "No subscription found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if subscription.status == Subscription.Status.CANCELLED:
            return Response(
                {"detail": "Subscription is already cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subscription.cancel_at_period_end = True
        subscription.save(update_fields=["cancel_at_period_end"])

        return Response(
            {
                "detail": "Subscription will be cancelled at the end of the billing cycle."
            }
        )


class CenterResumeSubscriptionView(APIView):
    """Center admin: resume a cancelled subscription before the billing cycle ends."""

    permission_classes = [permissions.IsAuthenticated, IsCenterAdmin]

    def post(self, request):
        tenant = request.tenant
        if not tenant:
            return Response(
                {"detail": "No center context."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            subscription = Subscription.objects.get(center=tenant)
        except Subscription.DoesNotExist:
            return Response(
                {"detail": "No subscription found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not subscription.cancel_at_period_end:
            return Response(
                {"detail": "Subscription is not scheduled for cancellation."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if subscription.status == Subscription.Status.CANCELLED:
            return Response(
                {
                    "detail": "Subscription is already cancelled. Please start a new subscription."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        subscription.cancel_at_period_end = False
        subscription.save(update_fields=["cancel_at_period_end"])

        return Response({"detail": "Subscription has been resumed."})


class CenterChangePlanView(APIView):
    """Center admin: change subscription plan to an active plan."""

    permission_classes = [permissions.IsAuthenticated, IsCenterAdmin]

    def post(self, request):
        tenant = request.tenant
        if not tenant:
            return Response(
                {"detail": "No center context."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            subscription = Subscription.objects.select_related("plan").get(
                center=tenant
            )
        except Subscription.DoesNotExist:
            return Response(
                {"detail": "No subscription found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        plan_id = request.data.get("plan_id")
        if not plan_id:
            return Response(
                {"detail": "plan_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            new_plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response(
                {"detail": "Invalid or inactive plan selected."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if subscription.plan_id == new_plan.id:
            return Response(
                {"detail": "You are already on this plan."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_plan = subscription.plan

        # Validations against constraints
        # Only check staff limits on upgrades, not downgrades
        if new_plan.price > old_plan.price and new_plan.max_staff != -1:
            from core.tenants.models import Staff

            current_staff = Staff.objects.filter(center=tenant).count()
            if current_staff > new_plan.max_staff:
                return Response(
                    {
                        "detail": f"Cannot downgrade. You have {current_staff} staff members, but this plan allows only {new_plan.max_staff}. Please remove {current_staff - new_plan.max_staff} staff member(s) first."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if new_plan.max_reports != -1:
            from django.utils import timezone as tz

            from apps.diagnostics.models import Report

            now = tz.now()
            current_reports = Report.objects.filter(
                test_order__center=tenant,
                created_at__year=now.year,
                created_at__month=now.month,
                is_deleted=False,
            ).count()
            if current_reports > new_plan.max_reports:
                return Response(
                    {
                        "detail": f"Cannot downgrade. You have created {current_reports} reports this month, which exceeds this plan's limit of {new_plan.max_reports}."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Determine upgrade vs downgrade flow
        is_upgrade_requiring_payment = new_plan.price > old_plan.price

        require_payment = False
        invoice_id = None

        if is_upgrade_requiring_payment:
            from decimal import ROUND_UP, Decimal

            from django.utils import timezone as tz

            pending_invoices = Invoice.objects.filter(
                subscription=subscription,
                status__in=[Invoice.Status.PENDING, Invoice.Status.OVERDUE],
            ).order_by("due_date")

            # Calculate prorated amount based on remaining billing days
            days_remaining = (subscription.billing_date - tz.now().date()).days
            if days_remaining < 0:
                days_remaining = 0
            daily_diff = (new_plan.price - old_plan.price) / Decimal("30")
            prorated_amount = (
                (daily_diff * Decimal(days_remaining)).quantize(
                    Decimal("0.01"), rounding=ROUND_UP
                )
                if days_remaining > 0
                else Decimal("0.01")
            )

            if pending_invoices.exists():
                for inv in pending_invoices:
                    inv.amount = prorated_amount
                    inv.target_plan = new_plan
                    inv.save(update_fields=["amount", "target_plan"])
                require_payment = True
                invoice_id = pending_invoices.first().id
            else:
                new_inv = Invoice.objects.create(
                    subscription=subscription,
                    amount=prorated_amount,
                    due_date=tz.now().date(),
                    status=Invoice.Status.PENDING,
                    target_plan=new_plan,
                )
                require_payment = True
                invoice_id = new_inv.id
        else:
            # Downgrades, same-price transitions, or free trials take immediate effect
            subscription.plan = new_plan
            if subscription.cancel_at_period_end:
                subscription.cancel_at_period_end = False
            subscription.save(update_fields=["plan", "cancel_at_period_end"])

            # Adjust pending invoice prices downwards
            pending_invoices = Invoice.objects.filter(
                subscription=subscription,
                status__in=[Invoice.Status.PENDING, Invoice.Status.OVERDUE],
            ).order_by("due_date")
            for inv in pending_invoices:
                inv.amount = new_plan.price
                inv.target_plan = None
                inv.save(update_fields=["amount", "target_plan"])

        # Invalidate cache
        from django.core.cache import cache

        cache.delete(f"sub_status:{tenant.id}")

        return Response(
            {
                "detail": f"Successfully changed plan to {new_plan.name}.",
                "require_payment": require_payment,
                "invoice_id": invoice_id,
            }
        )


class SubscriptionStatusView(APIView):
    """Any authenticated user: check subscription status for their center."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant = request.tenant
        if not tenant:
            return Response(
                {"status": "NONE", "is_blocked": False},
            )

        from django.core.cache import cache

        from core.tenants.models import Staff

        cache_key = f"sub_status:{tenant.id}"
        cached = cache.get(cache_key)

        max_staff = -1
        if cached:
            sub_status = cached
        else:
            try:
                sub = (
                    Subscription.objects.select_related("plan")
                    .filter(
                        center=tenant,
                    )
                    .latest("started_at")
                )
                sub_status = sub.status
                max_staff = sub.plan.max_staff
            except Subscription.DoesNotExist:
                sub_status = "NONE"
            cache.set(cache_key, sub_status, 300)

        # If we got status from cache, still need max_staff
        if cached:
            try:
                sub = (
                    Subscription.objects.select_related("plan")
                    .filter(
                        center=tenant,
                    )
                    .latest("started_at")
                )
                max_staff = sub.plan.max_staff
            except Subscription.DoesNotExist:
                pass

        is_blocked = sub_status in ("EXPIRED", "CANCELLED", "NONE", "INACTIVE")
        block_reason = ""
        if sub_status == "INACTIVE":
            block_reason = "payment_required"
        elif is_blocked:
            block_reason = "subscription_inactive"

        # Also block ACTIVE subscriptions with unpaid renewal invoices
        has_pending_invoice = False
        pending_invoice_amount = None
        if sub_status == "ACTIVE" and not is_blocked:
            pending_inv = (
                Invoice.objects.filter(
                    subscription__center=tenant,
                    status__in=(
                        Invoice.Status.PENDING,
                        Invoice.Status.OVERDUE,
                    ),
                )
                .order_by("due_date")
                .first()
            )
            if pending_inv:
                has_pending_invoice = True
                pending_invoice_amount = str(pending_inv.amount)

        if sub_status == "INACTIVE":
            # Fetch invoice amount for the paywall
            pending_inv = (
                Invoice.objects.filter(
                    subscription__center=tenant,
                    status__in=(
                        Invoice.Status.PENDING,
                        Invoice.Status.OVERDUE,
                    ),
                )
                .order_by("due_date")
                .first()
            )
            if pending_inv:
                has_pending_invoice = True
                pending_invoice_amount = str(pending_inv.amount)

        current_staff_count = Staff.objects.filter(center=tenant).count()
        staff_limit_reached = max_staff != -1 and current_staff_count >= max_staff

        # Report usage this month
        max_reports = -1
        with contextlib.suppress(Exception):
            max_reports = sub.plan.max_reports

        from django.utils import timezone as tz

        from apps.diagnostics.models import Report

        now = tz.now()
        current_report_count = Report.objects.filter(
            test_order__center=tenant,
            created_at__year=now.year,
            created_at__month=now.month,
            is_deleted=False,
        ).count()
        report_limit_reached = max_reports != -1 and current_report_count >= max_reports

        return Response(
            {
                "status": sub_status,
                "is_blocked": is_blocked,
                "block_reason": block_reason,
                "has_pending_invoice": has_pending_invoice,
                "pending_invoice_amount": pending_invoice_amount,
                "center_name": tenant.name,
                "max_staff": max_staff,
                "current_staff_count": current_staff_count,
                "staff_limit_reached": staff_limit_reached,
                "max_reports": max_reports,
                "current_report_count": current_report_count,
                "report_limit_reached": report_limit_reached,
            }
        )


class CenterInvoiceListView(APIView):
    """Center admin: list own invoices with submission status."""

    permission_classes = [permissions.IsAuthenticated, IsCenterAdmin]

    def get(self, request):
        tenant = request.tenant
        if not tenant:
            return Response(
                {"detail": "No center found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        invoices = Invoice.objects.filter(
            subscription__center=tenant,
        ).select_related("subscription__center")
        data = InvoiceSerializer(invoices, many=True).data
        # Attach latest submission status per invoice
        for inv_data in data:
            latest = (
                PaymentSubmission.objects.filter(
                    invoice_id=inv_data["id"],
                )
                .order_by("-submitted_at")
                .first()
            )
            if latest:
                inv_data["submission"] = {
                    "id": latest.id,
                    "status": latest.status,
                    "transaction_id": latest.transaction_id,
                    "admin_notes": latest.admin_notes,
                }
            else:
                inv_data["submission"] = None
        return Response(data)


class CenterSubmitPaymentView(APIView):
    """Center admin: submit payment proof for a pending invoice."""

    permission_classes = [permissions.IsAuthenticated, IsCenterAdmin]

    def post(self, request, invoice_id):
        tenant = request.tenant
        if not tenant:
            return Response(
                {"detail": "No center found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            invoice = Invoice.objects.get(
                id=invoice_id,
                subscription__center=tenant,
            )
        except Invoice.DoesNotExist:
            return Response(
                {"detail": "Invoice not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if invoice.status == Invoice.Status.PAID:
            return Response(
                {"detail": "This invoice is already paid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check for existing pending submission
        existing = PaymentSubmission.objects.filter(
            invoice=invoice,
            status=PaymentSubmission.Status.PENDING,
        ).first()
        if existing:
            return Response(
                {
                    "detail": (
                        "A payment submission is already pending "
                        "review for this invoice."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SubmitPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payment_method = PaymentInfo.objects.get(
                id=serializer.validated_data["payment_method_id"],
                is_active=True,
            )
        except PaymentInfo.DoesNotExist:
            return Response(
                {"detail": "Invalid payment method."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        submission = PaymentSubmission.objects.create(
            invoice=invoice,
            payment_method=payment_method,
            transaction_id=serializer.validated_data["transaction_id"],
            submitted_by=request.user,
        )

        return Response(
            {
                "detail": ("Payment submitted successfully. Awaiting verification."),
                "submission": PaymentSubmissionSerializer(
                    submission,
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def patch(self, request, invoice_id):
        """Update transaction_id on a pending submission."""
        tenant = request.tenant
        if not tenant:
            return Response(
                {"detail": "No center found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            invoice = Invoice.objects.get(
                id=invoice_id,
                subscription__center=tenant,
            )
        except Invoice.DoesNotExist:
            return Response(
                {"detail": "Invoice not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        submission = PaymentSubmission.objects.filter(
            invoice=invoice,
            status=PaymentSubmission.Status.PENDING,
        ).first()
        if not submission:
            return Response(
                {"detail": "No pending submission to edit."},
                status=status.HTTP_404_NOT_FOUND,
            )

        new_trx = request.data.get("transaction_id", "").strip()
        if not new_trx:
            return Response(
                {"detail": "Transaction ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        submission.transaction_id = new_trx
        submission.save(update_fields=["transaction_id"])

        return Response(
            {
                "detail": "Transaction ID updated.",
                "submission": PaymentSubmissionSerializer(
                    submission,
                ).data,
            },
        )


# ── Superadmin Views ─────────────────────────────────────────────


class SuperadminSubscriptionListView(APIView):
    """Superadmin: list all subscriptions across centers."""

    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        subscriptions = (
            Subscription.objects.select_related("plan", "center")
            .prefetch_related("invoices")
            .order_by("-started_at")
        )

        # Optional filters
        status_filter = request.query_params.get("status")
        if status_filter:
            subscriptions = subscriptions.filter(status=status_filter.upper())

        search = request.query_params.get("search", "").strip()
        if search:
            subscriptions = subscriptions.filter(
                center__name__icontains=search,
            )

        data = []
        for sub in subscriptions[:100]:
            data.append(
                {  # noqa: PERF401
                    "id": sub.id,
                    "center_id": sub.center.id,
                    "center_name": sub.center.name,
                    "center_domain": sub.center.domain,
                    "plan_id": sub.plan.id,
                    "plan_name": sub.plan.name,
                    "plan_price": str(sub.plan.price),
                    "status": sub.status,
                    "trial_start": (
                        sub.trial_start.isoformat() if sub.trial_start else None
                    ),
                    "trial_end": sub.trial_end.isoformat() if sub.trial_end else None,
                    "billing_date": (
                        sub.billing_date.isoformat() if sub.billing_date else None
                    ),
                    "started_at": sub.started_at.isoformat(),
                    "invoices_count": sub.invoices.count(),
                    "pending_invoices": sub.invoices.filter(
                        status=Invoice.Status.PENDING,
                    ).count(),
                }
            )

        return Response(data)

    def post(self, request):
        """Create a new subscription for a center."""
        serializer = SuperadminSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sub = serializer.save()

        logger.info(
            "Subscription created for %s by superadmin %s",
            sub.center.name,
            request.user.username,
        )

        # Invalidate cached status
        from django.core.cache import cache

        cache.delete(f"sub_status:{sub.center_id}")

        return Response(
            SuperadminSubscriptionSerializer(sub).data,
            status=status.HTTP_201_CREATED,
        )


class SuperadminSubscriptionDetailView(APIView):
    """Superadmin: retrieve, update, or delete a single subscription."""

    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def _get_subscription(self, subscription_id):
        try:
            return Subscription.objects.select_related("center", "plan").get(
                pk=subscription_id,
            )
        except Subscription.DoesNotExist:
            return None

    def get(self, request, subscription_id):
        sub = self._get_subscription(subscription_id)
        if not sub:
            return Response(
                {"detail": "Subscription not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(SuperadminSubscriptionSerializer(sub).data)

    def patch(self, request, subscription_id):
        sub = self._get_subscription(subscription_id)
        if not sub:
            return Response(
                {"detail": "Subscription not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = SuperadminSubscriptionSerializer(
            sub, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        sub = serializer.save()

        logger.info(
            "Subscription #%s updated by superadmin %s",
            sub.id,
            request.user.username,
        )

        # Invalidate cached status
        from django.core.cache import cache

        cache.delete(f"sub_status:{sub.center_id}")

        return Response(SuperadminSubscriptionSerializer(sub).data)

    def delete(self, request, subscription_id):
        sub = self._get_subscription(subscription_id)
        if not sub:
            return Response(
                {"detail": "Subscription not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        center_name = sub.center.name
        center_id = sub.center_id
        sub.delete()

        logger.info(
            "Subscription deleted for %s by superadmin %s",
            center_name,
            request.user.username,
        )

        # Invalidate cached status
        from django.core.cache import cache

        cache.delete(f"sub_status:{center_id}")

        return Response(status=status.HTTP_204_NO_CONTENT)


class SuperadminInvoiceListView(APIView):
    """Superadmin: list invoices with filters."""

    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        invoices = Invoice.objects.select_related(
            "subscription__center",
            "subscription__plan",
        ).order_by("-created_at")

        status_filter = request.query_params.get("status")
        if status_filter:
            invoices = invoices.filter(status=status_filter.upper())

        center_id = request.query_params.get("center")
        if center_id:
            invoices = invoices.filter(
                subscription__center_id=center_id,
            )

        data = []
        for inv in invoices[:100]:
            data.append(
                {  # noqa: PERF401
                    "id": inv.id,
                    "center_name": inv.subscription.center.name,
                    "center_domain": inv.subscription.center.domain,
                    "plan_name": inv.subscription.plan.name,
                    "amount": str(inv.amount),
                    "status": inv.status,
                    "payment_method": inv.payment_method,
                    "due_date": inv.due_date.isoformat(),
                    "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
                    "transaction_id": inv.transaction_id,
                    "notes": inv.notes,
                    "created_at": inv.created_at.isoformat(),
                }
            )

        return Response(data)


class SuperadminInvoiceMarkPaidView(APIView):
    """Superadmin: mark an invoice as paid and activate subscription."""

    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def post(self, request, invoice_id):
        try:
            invoice = Invoice.objects.select_related(
                "subscription",
            ).get(pk=invoice_id)
        except Invoice.DoesNotExist:
            return Response(
                {"detail": "Invoice not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if invoice.status == Invoice.Status.PAID:
            return Response(
                {"detail": "Invoice is already paid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update invoice
        invoice.status = Invoice.Status.PAID
        invoice.paid_at = timezone.now()
        invoice.payment_method = request.data.get(
            "payment_method", invoice.payment_method
        )
        invoice.transaction_id = request.data.get(
            "transaction_id", invoice.transaction_id
        )
        invoice.notes = request.data.get("notes", invoice.notes)
        invoice.save()

        # Activate subscription
        sub = invoice.subscription

        # Apply asynchronous plan upgrade
        if invoice.target_plan:
            sub.plan = invoice.target_plan

        sub.status = Subscription.Status.ACTIVE
        sub.save(update_fields=["status", "plan"])

        logger.info(
            "Invoice #%s marked paid by superadmin %s",
            invoice.id,
            request.user.username,
        )

        # Send payment received email
        center = sub.center
        if center.email:
            send_email_async(
                EmailType.PAYMENT_RECEIVED,
                recipient=center.email,
                context={
                    "center_name": center.name,
                    "amount": str(invoice.amount),
                    "plan_name": sub.plan.name,
                },
            )

        return Response(
            {
                "detail": f"Invoice #{invoice.id} marked as paid. Subscription activated.",
                "invoice": InvoiceSerializer(invoice).data,
            }
        )


class SuperadminInvoiceMarkUnpaidView(APIView):
    """Superadmin: revert a paid invoice back to pending."""

    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def post(self, request, invoice_id):
        try:
            invoice = Invoice.objects.select_related(
                "subscription",
            ).get(pk=invoice_id)
        except Invoice.DoesNotExist:
            return Response(
                {"detail": "Invoice not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if invoice.status != Invoice.Status.PAID:
            return Response(
                {"detail": "Invoice is not paid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Revert invoice
        invoice.status = Invoice.Status.PENDING
        invoice.paid_at = None
        invoice.save(update_fields=["status", "paid_at"])

        logger.info(
            "Invoice #%s reverted to unpaid by superadmin %s",
            invoice.id,
            request.user.username,
        )

        return Response(
            {
                "detail": f"Invoice #{invoice.id} reverted to pending.",
                "invoice": InvoiceSerializer(invoice).data,
            }
        )


class SuperadminExtendTrialView(APIView):
    """Superadmin: extend a center's trial period by N days."""

    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def post(self, request, subscription_id):
        try:
            sub = Subscription.objects.select_related("center").get(
                pk=subscription_id,
            )
        except Subscription.DoesNotExist:
            return Response(
                {"detail": "Subscription not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        days = request.data.get("days")
        if not days or not isinstance(days, int) or days < 1:
            return Response(
                {"detail": 'Provide a positive integer "days" value.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from datetime import timedelta

        from django.core.cache import cache

        # If trial already expired, reset trial_end from now
        if sub.trial_end and sub.trial_end < timezone.now():
            sub.trial_end = timezone.now() + timedelta(days=days)
        elif sub.trial_end:
            sub.trial_end = sub.trial_end + timedelta(days=days)
        else:
            sub.trial_end = timezone.now() + timedelta(days=days)

        sub.trial_start = sub.trial_start or timezone.now()
        sub.status = Subscription.Status.TRIAL
        sub.billing_date = sub.trial_end.date()
        sub.save(
            update_fields=[
                "status",
                "trial_start",
                "trial_end",
                "billing_date",
            ]
        )

        # Invalidate cached status
        cache.delete(f"sub_status:{sub.center_id}")

        logger.info(
            "Trial extended by %d days for %s by superadmin %s",
            days,
            sub.center.name,
            request.user.username,
        )

        return Response(
            {
                "detail": f"Trial extended by {days} days for {sub.center.name}.",
                "subscription": SubscriptionSerializer(sub).data,
            }
        )


class SuperadminChangePlanView(APIView):
    """Superadmin: change a center's subscription plan and activate it."""

    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def post(self, request, subscription_id):
        try:
            sub = Subscription.objects.select_related("center", "plan").get(
                pk=subscription_id,
            )
        except Subscription.DoesNotExist:
            return Response(
                {"detail": "Subscription not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        plan_id = request.data.get("plan_id")
        if not plan_id:
            return Response(
                {"detail": 'Provide a "plan_id".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            new_plan = SubscriptionPlan.objects.get(pk=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response(
                {"detail": "Plan not found or inactive."},
                status=status.HTTP_404_NOT_FOUND,
            )

        from datetime import timedelta

        from django.core.cache import cache

        old_plan_name = sub.plan.name
        sub.plan = new_plan
        sub.status = Subscription.Status.ACTIVE
        sub.billing_date = (timezone.now() + timedelta(days=30)).date()
        sub.save(update_fields=["plan", "status", "billing_date"])

        # Invalidate cached status
        cache.delete(f"sub_status:{sub.center_id}")

        logger.info(
            "Plan changed from %s to %s for %s by superadmin %s",
            old_plan_name,
            new_plan.name,
            sub.center.name,
            request.user.username,
        )

        return Response(
            {
                "detail": (
                    f"Plan changed to {new_plan.name} for {sub.center.name}. "
                    f"Subscription activated."
                ),
                "subscription": SubscriptionSerializer(sub).data,
            }
        )


class SuperadminCreateInvoiceView(APIView):
    """Superadmin: create a custom invoice for a center's subscription."""

    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def post(self, request, subscription_id):
        try:
            sub = Subscription.objects.select_related("center", "plan").get(
                pk=subscription_id,
            )
        except Subscription.DoesNotExist:
            return Response(
                {"detail": "Subscription not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        from datetime import date
        from decimal import Decimal, InvalidOperation

        # Validate amount
        raw_amount = request.data.get("amount")
        if not raw_amount:
            return Response(
                {"detail": 'Provide an "amount".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            amount = Decimal(str(raw_amount))
            if amount <= 0:
                raise ValueError
        except (InvalidOperation, ValueError):
            return Response(
                {"detail": "Amount must be a positive number."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate due_date
        raw_due_date = request.data.get("due_date")
        if not raw_due_date:
            return Response(
                {"detail": 'Provide a "due_date" (YYYY-MM-DD).'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            due_date = date.fromisoformat(raw_due_date)
        except (ValueError, TypeError):
            return Response(
                {"detail": "Invalid due_date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        notes = request.data.get("notes", "")

        invoice = Invoice.objects.create(
            subscription=sub,
            amount=amount,
            due_date=due_date,
            status=Invoice.Status.PENDING,
            notes=notes,
        )

        logger.info(
            "Custom invoice #%s created for %s (৳%s) by superadmin %s",
            invoice.id,
            sub.center.name,
            amount,
            request.user.username,
        )

        # Send email notification
        from apps.subscriptions.tasks import _get_center_admin_email

        admin_email = _get_center_admin_email(sub.center)
        if admin_email:
            send_email_async(
                EmailType.INVOICE_GENERATED,
                recipient=admin_email,
                context={
                    "center_name": sub.center.name,
                    "amount": str(amount),
                    "due_date": str(due_date),
                },
            )

        return Response(
            {
                "detail": (
                    f"Invoice #{invoice.id} created for {sub.center.name} "
                    f"(৳{amount}, due {due_date})."
                ),
                "invoice": InvoiceSerializer(invoice).data,
            },
            status=status.HTTP_201_CREATED,
        )


class SuperadminPaymentSubmissionListView(APIView):
    """Superadmin: list all payment submissions."""

    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        qs = PaymentSubmission.objects.select_related(
            "invoice__subscription__center",
            "payment_method",
            "submitted_by",
        ).all()

        # Filter by status
        sub_status = request.query_params.get("status")
        if sub_status:
            qs = qs.filter(status=sub_status)

        # Search by center name or transaction ID
        search = request.query_params.get("search")
        if search:
            from django.db.models import Q

            qs = qs.filter(
                Q(
                    invoice__subscription__center__name__icontains=search,
                )
                | Q(transaction_id__icontains=search)
            )

        return Response(
            PaymentSubmissionSerializer(qs[:100], many=True).data,
        )


class SuperadminVerifyPaymentView(APIView):
    """Superadmin: verify or reject a payment submission."""

    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def post(self, request, submission_id):
        from django.core.cache import cache

        try:
            submission = PaymentSubmission.objects.select_related(
                "invoice__subscription",
            ).get(id=submission_id)
        except PaymentSubmission.DoesNotExist:
            return Response(
                {"detail": "Submission not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        action = request.data.get("action")  # 'verify' or 'reject'
        if action not in ("verify", "reject"):
            return Response(
                {"detail": 'Action must be "verify" or "reject".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if submission.status != PaymentSubmission.Status.PENDING:
            return Response(
                {
                    "detail": (
                        f"This submission has already been {submission.status.lower()}."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if action == "verify":
            submission.status = PaymentSubmission.Status.VERIFIED
            submission.reviewed_at = timezone.now()
            submission.save()

            # Mark invoice as paid
            invoice = submission.invoice
            invoice.status = Invoice.Status.PAID
            invoice.paid_at = timezone.now()
            invoice.payment_method = (
                submission.payment_method.method if submission.payment_method else ""
            )
            invoice.transaction_id = submission.transaction_id
            invoice.save()

            # Activate subscription
            sub = invoice.subscription

            # Apply deferred target_plan upgrade
            if invoice.target_plan:
                sub.plan = invoice.target_plan

            if sub.status in (
                Subscription.Status.INACTIVE,
                Subscription.Status.EXPIRED,
            ):
                sub.status = Subscription.Status.ACTIVE

            sub.save(update_fields=["status", "plan"])
            # Clear cached subscription status
            cache.delete(f"sub_status:{sub.center_id}")

            return Response(
                {
                    "detail": (
                        f"Payment verified. Invoice #{invoice.id} "
                        f"marked as paid. Subscription activated."
                    ),
                },
            )

        # Reject
        submission.status = PaymentSubmission.Status.REJECTED
        submission.admin_notes = request.data.get(
            "reason",
            "",
        )
        submission.reviewed_at = timezone.now()
        submission.save()

        return Response(
            {
                "detail": (f"Payment submission #{submission.id} rejected."),
            },
        )
