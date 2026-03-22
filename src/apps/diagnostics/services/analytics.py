"""Analytics service for business intelligence dashboards.

Provides aggregated data for revenue, doctor performance,
patient retention, and turnaround time metrics.
"""

import logging
from datetime import timedelta

from django.db import models
from django.db.models import Count
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
from django.utils import timezone

from apps.diagnostics.models import Report, TestOrder

logger = logging.getLogger(__name__)


def revenue_by_test_type(center, start_date=None, end_date=None):
    """Revenue breakdown by test type for a center.

    Returns list of dicts: {test_type, test_type_name, total_revenue, count}
    """
    qs = TestOrder.objects.filter(
        center=center,
        status=TestOrder.Status.COMPLETED,
    ).select_related("test_type")

    if start_date:
        qs = qs.filter(created_at__gte=start_date)
    if end_date:
        qs = qs.filter(created_at__lte=end_date)

    from apps.diagnostics.models import CenterTestPricing

    results = (
        qs.values("test_type__id", "test_type__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    # Attach price from CenterTestPricing
    pricing = {
        p.test_type_id: p.price for p in CenterTestPricing.objects.filter(center=center)
    }

    data = []
    for row in results:
        price = pricing.get(row["test_type__id"], 0)
        data.append(
            {
                "test_type_id": row["test_type__id"],
                "test_type_name": row["test_type__name"],
                "count": row["count"],
                "total_revenue": float(price * row["count"]),
            }
        )
    return data


def revenue_trends(center, period="daily", days=30):
    """Revenue trends over time.

    Args:
        period: 'daily', 'weekly', or 'monthly'
        days: Number of days to look back

    Returns list of {date, revenue, count}
    """
    from apps.diagnostics.models import CenterTestPricing

    start = timezone.now() - timedelta(days=days)
    qs = TestOrder.objects.filter(
        center=center,
        status=TestOrder.Status.COMPLETED,
        created_at__gte=start,
    )

    trunc_fn = {"daily": TruncDate, "weekly": TruncWeek, "monthly": TruncMonth}
    trunc = trunc_fn.get(period, TruncDate)

    results = (
        qs.annotate(period=trunc("created_at"))
        .values("period")
        .annotate(count=Count("id"))
        .order_by("period")
    )

    pricing = {
        p.test_type_id: float(p.price)
        for p in CenterTestPricing.objects.filter(center=center)
    }

    # Calculate approximate revenue per period
    data = []
    for row in results:
        # Get average price for all orders in this period
        period_orders = qs.filter(created_at__date=row["period"]).values_list(
            "test_type_id", flat=True
        )
        revenue = sum(pricing.get(tid, 0) for tid in period_orders)
        data.append(
            {
                "date": row["period"].isoformat() if row["period"] else None,
                "count": row["count"],
                "revenue": revenue,
            }
        )
    return data


def revenue_by_doctor(center, start_date=None, end_date=None):
    """Revenue breakdown by referring doctor."""
    qs = TestOrder.objects.filter(
        center=center,
        status=TestOrder.Status.COMPLETED,
    ).exclude(referring_doctor_name="")

    if start_date:
        qs = qs.filter(created_at__gte=start_date)
    if end_date:
        qs = qs.filter(created_at__lte=end_date)

    from apps.diagnostics.models import CenterTestPricing

    pricing = {
        p.test_type_id: float(p.price)
        for p in CenterTestPricing.objects.filter(center=center)
    }

    results = (
        qs.values("referring_doctor_name")
        .annotate(
            patient_count=Count("patient", distinct=True),
            test_count=Count("id"),
        )
        .order_by("-test_count")
    )

    data = []
    for row in results:
        # Calculate revenue for this doctor's referrals
        doctor_orders = qs.filter(
            referring_doctor_name=row["referring_doctor_name"],
        ).values_list("test_type_id", flat=True)
        revenue = sum(pricing.get(tid, 0) for tid in doctor_orders)

        data.append(
            {
                "doctor_name": row["referring_doctor_name"],
                "patient_count": row["patient_count"],
                "test_count": row["test_count"],
                "total_revenue": revenue,
            }
        )
    return data


def patient_metrics(center, days=30):
    """New vs returning patient metrics."""
    now = timezone.now()
    start = now - timedelta(days=days)

    current_patients = (
        TestOrder.objects.filter(
            center=center,
            created_at__gte=start,
        )
        .values_list("patient_id", flat=True)
        .distinct()
    )

    # Patients who had tests before this period
    returning = (
        TestOrder.objects.filter(
            center=center,
            patient_id__in=current_patients,
            created_at__lt=start,
        )
        .values_list("patient_id", flat=True)
        .distinct()
    )
    returning_set = set(returning)

    total = len(set(current_patients))
    returning_count = len(returning_set)

    return {
        "total_patients": total,
        "new_patients": total - returning_count,
        "returning_patients": returning_count,
        "period_days": days,
    }


def turnaround_time_stats(center, days=30):
    """Average TAT by test type (order to verification)."""
    start = timezone.now() - timedelta(days=days)
    reports = Report.objects.filter(
        test_order__center=center,
        verified_at__isnull=False,
        created_at__gte=start,
        is_deleted=False,
    ).select_related("test_type", "test_order")

    tat_by_test = {}
    for report in reports:
        tat = (report.verified_at - report.test_order.created_at).total_seconds() / 3600
        test_name = report.test_type.name
        if test_name not in tat_by_test:
            tat_by_test[test_name] = []
        tat_by_test[test_name].append(tat)

    data = []
    for test_name, tats in tat_by_test.items():
        data.append(
            {
                "test_type_name": test_name,
                "avg_tat_hours": round(sum(tats) / len(tats), 1),
                "min_tat_hours": round(min(tats), 1),
                "max_tat_hours": round(max(tats), 1),
                "count": len(tats),
            }
        )
    return sorted(data, key=lambda x: x['avg_tat_hours'])


def invoice_revenue_summary(center, days=30):
    """Revenue summary from invoices (the real billing source).

    Returns today/week/month totals and breakdown by item type.
    """
    from datetime import date as dt_date

    from django.db.models import Sum

    from apps.payments.models import Invoice, InvoiceItem

    now = timezone.now()
    start = now - timedelta(days=days)
    today = dt_date.today()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    base_qs = Invoice.objects.filter(
        center=center,
        status__in=['PAID', 'ISSUED'],
    )

    # Period totals
    period_qs = base_qs.filter(created_at__gte=start)
    today_qs = base_qs.filter(created_at__date=today)
    week_qs = base_qs.filter(created_at__date__gte=week_start)
    month_qs = base_qs.filter(created_at__date__gte=month_start)

    def _agg(qs):
        result = qs.aggregate(
            total=Sum('total'),
            count=Count('id'),
        )
        return {
            'total': float(result['total'] or 0),
            'count': result['count'],
        }

    # Breakdown by item type
    item_breakdown = (
        InvoiceItem.objects.filter(
            invoice__center=center,
            invoice__status__in=['PAID', 'ISSUED'],
            invoice__created_at__gte=start,
        )
        .values('item_type')
        .annotate(
            total=Sum('total_price'),
            count=Count('id'),
        )
        .order_by('-total')
    )

    by_type = []
    for row in item_breakdown:
        by_type.append({
            'item_type': row['item_type'],
            'total': float(row['total'] or 0),
            'count': row['count'],
        })

    return {
        'period': _agg(period_qs),
        'today': _agg(today_qs),
        'this_week': _agg(week_qs),
        'this_month': _agg(month_qs),
        'by_item_type': by_type,
    }


def appointment_stats(center, days=30):
    """Appointment statistics: counts by status, completion rate, by doctor."""
    from apps.appointments.models import Appointment

    start = timezone.now() - timedelta(days=days)
    qs = Appointment.objects.filter(
        center=center,
        created_at__gte=start,
    )

    total = qs.count()
    by_status = dict(qs.values_list('status').annotate(c=Count('id')).values_list('status', 'c'))

    completed = by_status.get('COMPLETED', 0)
    cancelled = by_status.get('CANCELLED', 0)
    pending = by_status.get('PENDING', 0)
    confirmed = by_status.get('CONFIRMED', 0)
    completion_rate = round((completed / total) * 100, 1) if total else 0

    # By doctor
    by_doctor = list(
        qs.filter(doctor__isnull=False)
        .values('doctor__user__first_name', 'doctor__user__last_name')
        .annotate(
            total=Count('id'),
            completed=Count('id', filter=models.Q(status='COMPLETED')),
        )
        .order_by('-total')[:10]
    )

    doctor_data = []
    for row in by_doctor:
        name = f"{row['doctor__user__first_name']} {row['doctor__user__last_name']}".strip()
        doctor_data.append({
            'doctor_name': name,
            'total': row['total'],
            'completed': row['completed'],
        })

    return {
        'total': total,
        'completed': completed,
        'cancelled': cancelled,
        'pending': pending,
        'confirmed': confirmed,
        'completion_rate': completion_rate,
        'by_doctor': doctor_data,
    }


def today_summary(center):
    """Quick 'today at a glance' for the admin dashboard."""
    from datetime import date as dt_date

    from django.db.models import Sum

    from apps.appointments.models import Appointment
    from apps.payments.models import Invoice

    today = dt_date.today()

    # Invoices today
    invoices_today = Invoice.objects.filter(
        center=center,
        created_at__date=today,
        status__in=['PAID', 'ISSUED'],
    )
    inv_agg = invoices_today.aggregate(
        total=Sum('total'),
        count=Count('id'),
    )

    # Appointments today
    appts_today = Appointment.objects.filter(center=center, date=today)
    appt_total = appts_today.count()
    appt_completed = appts_today.filter(status='COMPLETED').count()

    # Test orders today
    test_orders_today = TestOrder.objects.filter(
        center=center,
        created_at__date=today,
    ).count()

    # Reports created today
    reports_today = Report.objects.filter(
        test_order__center=center,
        created_at__date=today,
        is_deleted=False,
    ).count()

    return {
        'revenue': float(inv_agg['total'] or 0),
        'invoices': inv_agg['count'],
        'appointments_total': appt_total,
        'appointments_completed': appt_completed,
        'test_orders': test_orders_today,
        'reports': reports_today,
    }

