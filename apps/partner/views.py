from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import F, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from apps.transaction.models import TransactionHeader
from apps.transaction.services import PurchaseService, SalesService

from .models import Contact
from .services import (
    PartnerForm,
    apply_filters,
    build_export_response,
    paginate_contacts,
    partner_stats,
    save_form,
)


def _normalize_money(value):
    if value is None:
        return 0
    if isinstance(value, Decimal):
        return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _normalize_money_fields(obj, fields):
    for field in fields:
        setattr(obj, field, _normalize_money(getattr(obj, field, 0)))
    return obj


class PartnerListView(View):
    template_name = "partner/partner_list.html"

    def get(self, request):
        active_section = (request.GET.get("section")
                          or "partner").strip().lower()
        if active_section not in {"partner", "hutang", "piutang"}:
            active_section = "partner"

        # Partner tab data
        queryset = Contact.objects.all().order_by("name")
        filtered_queryset = apply_filters(queryset, request.GET)
        partners_page = paginate_contacts(
            filtered_queryset, request.GET.get("page"), per_page=10
        )
        for partner in partners_page.object_list:
            _normalize_money_fields(partner, ("current_balance",))

        today = timezone.now().date()
        outstanding_expr = F("total_amount") - F("amount_paid")

        # Hutang tab data (purchase payables)
        payables_base = (
            TransactionHeader.objects.filter(
                trx_type="PURCHASE", total_amount__gt=F("amount_paid")
            )
            .select_related("contact", "branch")
            .order_by("-due_date", "-created_at")
        )
        payables_qs = payables_base

        hutang_q = (request.GET.get("hutang_q") or "").strip()
        if hutang_q:
            payables_qs = payables_qs.filter(
                Q(invoice_number__icontains=hutang_q)
                | Q(contact__name__icontains=hutang_q)
            )

        hutang_status = (request.GET.get("hutang_status") or "").strip()
        if hutang_status == "overdue":
            payables_qs = payables_qs.filter(due_date__lt=today)
        elif hutang_status == "pending":
            payables_qs = payables_qs.filter(amount_paid=0)
        elif hutang_status == "partial":
            payables_qs = payables_qs.filter(amount_paid__gt=0)

        hutang_supplier = (request.GET.get("hutang_supplier") or "").strip()
        if hutang_supplier.isdigit():
            payables_qs = payables_qs.filter(contact_id=int(hutang_supplier))

        hutang_due_before = (request.GET.get(
            "hutang_due_before") or "").strip()
        if hutang_due_before:
            payables_qs = payables_qs.filter(due_date__lte=hutang_due_before)

        payables_page = Paginator(payables_qs, 10).get_page(
            request.GET.get("hutang_page"))
        for payable in payables_page.object_list:
            PurchaseService.attach_ui_fields(payable)
            _normalize_money_fields(
                payable,
                ("total_amount", "amount_paid", "outstanding"),
            )

        hutang_total_outstanding = payables_qs.aggregate(
            total=Coalesce(Sum(outstanding_expr), Decimal("0"))
        )["total"]
        hutang_overdue_total = payables_qs.filter(due_date__lt=today).aggregate(
            total=Coalesce(Sum(outstanding_expr), Decimal("0"))
        )["total"]
        hutang_week_due = payables_qs.filter(
            due_date__range=(today, today + timedelta(days=7))
        ).aggregate(total=Coalesce(Sum(outstanding_expr), Decimal("0")))["total"]

        # Piutang tab data (sales receivables)
        receivables_base = (
            TransactionHeader.objects.filter(
                trx_type="SALE", total_amount__gt=F("amount_paid")
            )
            .select_related("contact", "branch")
            .order_by("-due_date", "-created_at")
        )
        receivables_qs = receivables_base

        piutang_q = (request.GET.get("piutang_q") or "").strip()
        if piutang_q:
            receivables_qs = receivables_qs.filter(
                Q(invoice_number__icontains=piutang_q)
                | Q(contact__name__icontains=piutang_q)
            )

        piutang_status = (request.GET.get("piutang_status") or "").strip()
        if piutang_status == "overdue":
            receivables_qs = receivables_qs.filter(due_date__lt=today)
        elif piutang_status == "pending":
            receivables_qs = receivables_qs.filter(amount_paid=0)
        elif piutang_status == "partial":
            receivables_qs = receivables_qs.filter(amount_paid__gt=0)

        piutang_customer = (request.GET.get("piutang_customer") or "").strip()
        if piutang_customer.isdigit():
            receivables_qs = receivables_qs.filter(
                contact_id=int(piutang_customer))

        piutang_due_before = (request.GET.get(
            "piutang_due_before") or "").strip()
        if piutang_due_before:
            receivables_qs = receivables_qs.filter(
                due_date__lte=piutang_due_before)

        receivables_page = Paginator(receivables_qs, 10).get_page(
            request.GET.get("piutang_page")
        )
        for receivable in receivables_page.object_list:
            SalesService.attach_ui_fields(receivable)
            _normalize_money_fields(
                receivable,
                ("total_amount", "amount_paid", "outstanding"),
            )

        piutang_total_outstanding = receivables_qs.aggregate(
            total=Coalesce(Sum(outstanding_expr), Decimal("0"))
        )["total"]
        piutang_overdue_total = receivables_qs.filter(due_date__lt=today).aggregate(
            total=Coalesce(Sum(outstanding_expr), Decimal("0"))
        )["total"]
        piutang_week_due = receivables_qs.filter(
            due_date__range=(today, today + timedelta(days=7))
        ).aggregate(total=Coalesce(Sum(outstanding_expr), Decimal("0")))["total"]

        context = {
            "active_section": active_section,
            "partners": partners_page,
            "payables": payables_page,
            "receivables": receivables_page,
            "suppliers": Contact.objects.filter(
                contact_type__in=["SUPPLIER", "BOTH"]
            ).order_by("name"),
            "customers": Contact.objects.filter(
                contact_type__in=["CUSTOMER", "BOTH"]
            ).order_by("name"),
            "hutang_total_outstanding": int(hutang_total_outstanding),
            "hutang_overdue_total": int(hutang_overdue_total),
            "hutang_week_due": int(hutang_week_due),
            "hutang_count": payables_qs.count(),
            "piutang_total_outstanding": int(piutang_total_outstanding),
            "piutang_overdue_total": int(piutang_overdue_total),
            "piutang_week_due": int(piutang_week_due),
            "piutang_count": receivables_qs.count(),
            **partner_stats(),
        }
        return render(request, self.template_name, context)


class PartnerCreateView(View):
    template_name = "partner/partner_form.html"

    def get(self, request):
        return render(request, self.template_name, {"form": PartnerForm(), "partner": None})

    def post(self, request):
        form = PartnerForm(request.POST)
        if form.is_valid():
            save_form(form)
            messages.success(request, "Partner berhasil ditambahkan.")
            return redirect("partner:partner_list")
        return render(request, self.template_name, {"form": form, "partner": None})


class PartnerUpdateView(View):
    template_name = "partner/partner_form.html"

    def get(self, request, pk):
        partner = get_object_or_404(Contact, pk=pk)
        form = PartnerForm(instance=partner)
        return render(request, self.template_name, {"form": form, "partner": partner})

    def post(self, request, pk):
        partner = get_object_or_404(Contact, pk=pk)
        form = PartnerForm(request.POST, instance=partner)
        if form.is_valid():
            save_form(form)
            messages.success(request, "Partner berhasil diperbarui.")
            return redirect("partner:partner_list")
        return render(request, self.template_name, {"form": form, "partner": partner})


class PartnerDeleteView(View):
    def post(self, request, pk):
        partner = get_object_or_404(Contact, pk=pk)
        partner.delete()
        messages.success(request, "Partner berhasil dihapus.")
        return redirect("partner:partner_list")

    def delete(self, request, pk):
        return self.post(request, pk)


class PartnerExportView(View):
    def get(self, request):
        queryset = Contact.objects.all().order_by("name")
        filtered_queryset = apply_filters(queryset, request.GET)
        return build_export_response(filtered_queryset)
