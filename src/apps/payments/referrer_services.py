from decimal import Decimal

from django.db import transaction
from django.db.models import DecimalField, ExpressionWrapper, F, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import serializers

from .models import Invoice, ReferrerSettlement, ReferrerSettlementItem

ZERO = Decimal("0.00")


def get_referrer_due_queryset(referrer, center):
    """Return commission-eligible invoices with settled/due annotations."""
    settled_amount = Coalesce(
        Sum("referrer_settlement_items__allocated_amount"),
        Value(ZERO),
        output_field=DecimalField(max_digits=10, decimal_places=2),
    )
    due_amount = ExpressionWrapper(
        F("commission_amount") - settled_amount,
        output_field=DecimalField(max_digits=10, decimal_places=2),
    )
    return (
        Invoice.objects.filter(
            center=center,
            referrer=referrer,
            status=Invoice.Status.PAID,
            commission_amount__gt=ZERO,
        )
        .select_related("patient", "referrer")
        .annotate(
            settled_amount=settled_amount,
            due_amount=due_amount,
        )
        .filter(due_amount__gt=ZERO)
        .order_by("paid_at", "created_at", "id")
    )


def get_invoice_remaining_commission(invoice):
    settled = (
        invoice.referrer_settlement_items.aggregate(
            total=Coalesce(
                Sum("allocated_amount"),
                Value(ZERO),
                output_field=DecimalField(max_digits=10, decimal_places=2),
            )
        )["total"]
        or ZERO
    )
    remaining = (invoice.commission_amount or ZERO) - settled
    return remaining if remaining > ZERO else ZERO


@transaction.atomic
def create_referrer_settlement(
    *,
    referrer,
    center,
    invoice_ids,
    amount_paid,
    payment_method,
    notes,
    user,
):
    if not invoice_ids:
        raise serializers.ValidationError(
            {"invoice_ids": "At least one due invoice must be selected."}
        )
    if amount_paid <= ZERO:
        raise serializers.ValidationError(
            {"amount_paid": "Amount paid must be greater than zero."}
        )

    due_qs = get_referrer_due_queryset(referrer, center).filter(id__in=invoice_ids)
    due_invoices = list(due_qs)
    if len(due_invoices) != len(set(invoice_ids)):
        raise serializers.ValidationError(
            {
                "invoice_ids": (
                    "One or more selected invoices are not eligible for this referrer."
                )
            }
        )

    selected_due = sum((invoice.due_amount for invoice in due_invoices), ZERO)
    if amount_paid > selected_due:
        raise serializers.ValidationError(
            {"amount_paid": "Amount paid cannot exceed the selected due amount."}
        )

    settlement = ReferrerSettlement.objects.create(
        referrer=referrer,
        center=center,
        amount_paid=amount_paid,
        payment_method=payment_method,
        paid_at=timezone.now(),
        notes=notes,
        created_by=user,
    )

    remaining = amount_paid
    allocations = []
    for invoice in due_invoices:
        if remaining <= ZERO:
            break
        allocate = min(invoice.due_amount, remaining)
        if allocate <= ZERO:
            continue
        allocations.append(
            ReferrerSettlementItem(
                settlement=settlement,
                invoice=invoice,
                allocated_amount=allocate,
            )
        )
        remaining -= allocate

    if remaining > ZERO:
        raise serializers.ValidationError(
            {"amount_paid": "Unable to allocate the full payment amount."}
        )

    ReferrerSettlementItem.objects.bulk_create(allocations)
    return settlement
