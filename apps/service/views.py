import csv
import re
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db import models
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from apps.common.escpos_builder import EscposBuilder, WindowsUsbEscposPrinter
from apps.inventory.models import Branch
from apps.partner.models import Contact
from apps.transaction.models import TransactionHeader
from apps.finance.models import FinancialAccount

from .models import ServiceTicket


User = get_user_model()


STATUS_UI = {
    "RECEIVED": {"label": "Diterima", "badge": "badge-received", "dot": "bg-slate-400"},
    "DIAGNOSING": {"label": "Pengecekan", "badge": "badge-diagnosing", "dot": "bg-blue-500"},
    "WAITING": {"label": "Menunggu Part", "badge": "badge-waiting", "dot": "bg-amber-500"},
    "REPAIRING": {"label": "Perbaikan", "badge": "badge-repairing", "dot": "bg-violet-500"},
    "DONE": {"label": "Siap Diambil", "badge": "badge-ready", "dot": "bg-emerald-500"},
    "PICKED": {"label": "Diambil", "badge": "badge-done", "dot": "bg-emerald-500"},
    "CANCELLED": {"label": "Batal", "badge": "badge-cancelled", "dot": "bg-red-500"},
}


def _as_decimal(value: str | None, default: Decimal = Decimal("0")) -> Decimal:
    if value is None:
        return default
    try:
        cleaned = str(value).strip().replace(".", "").replace(",", ".")
        if cleaned == "":
            return default
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return default


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except ValueError:
        return None


def _parse_date(value: str | None):
    if not value:
        return None
    try:
        return timezone.datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_contact_from_partner_input(value: str | None) -> Contact | None:
    if not value:
        return None
    raw = str(value).strip()
    # Accept plain numeric ID
    if raw.isdigit():
        return Contact.objects.filter(pk=int(raw)).first()
    # Accept "<id> | <name>" format
    match = re.match(r"^(\d+)\s*[|\-]", raw)
    if match:
        return Contact.objects.filter(pk=int(match.group(1))).first()
    # Fallback: try name exact (last resort)
    return Contact.objects.filter(name__iexact=raw).first()


def _next_ticket_number() -> str:
    last = ServiceTicket.objects.filter(
        ticket_number__startswith="SRV-").order_by("-id").first()
    if not last:
        return "SRV-0001"
    m = re.search(r"(\d+)$", last.ticket_number or "")
    if not m:
        return "SRV-0001"
    nxt = int(m.group(1)) + 1
    width = max(4, len(m.group(1)))
    return f"SRV-{nxt:0{width}d}"


class ServiceQueueView(View):
    template_name = "service/service_queue.html"

    def get(self, request):
        q = (request.GET.get("q") or "").strip()
        status = (request.GET.get("status") or "").strip()
        branch_id = _parse_int(request.GET.get("branch"))

        tickets = ServiceTicket.objects.select_related(
            "customer", "branch"
        ).order_by("-id")

        if branch_id:
            tickets = tickets.filter(branch_id=branch_id)

        base_for_stats = tickets

        if status:
            tickets = tickets.filter(status=status)

        if q:
            tickets = tickets.filter(
                models.Q(ticket_number__icontains=q)
                | models.Q(customer__name__icontains=q)
                | models.Q(device_name__icontains=q)
                | models.Q(serial_number__icontains=q)
                | models.Q(device_brand__icontains=q)
            )

        # Limit to keep page fast and allow attaching computed fields safely.
        tickets_list = list(tickets[:200])

        # Attach computed fields used by template
        for t in tickets_list:
            ui = STATUS_UI.get(
                t.status, {"label": t.status, "badge": "badge-received", "dot": "bg-slate-400"})
            setattr(t, "status_label", ui["label"])
            setattr(t, "status_badge", ui["badge"])
            setattr(t, "status_dot", ui["dot"])

        today = timezone.localdate()
        total_active = base_for_stats.exclude(
            status__in=["PICKED", "CANCELLED"]).count()
        waiting_parts = base_for_stats.filter(status="WAITING").count()
        ready_pickup = base_for_stats.filter(status="DONE").count()
        finished_today = base_for_stats.filter(
            status__in=["DONE", "PICKED"], updated_at__date=today
        ).count()

        context = {
            "tickets": tickets_list,
            "q": q,
            "status": status,
            "branch": branch_id or "",
            "branches": Branch.objects.filter(is_active=True).order_by("name"),
            "stats": {
                "total_active": total_active,
                "waiting_parts": waiting_parts,
                "ready_pickup": ready_pickup,
                "finished_today": finished_today,
            },
        }
        return render(request, self.template_name, context)


class ServiceCheckinView(View):
    template_name = "service/service_checkin.html"

    def get(self, request):
        form_data = request.session.pop('form_data', {})
        form_data_lists = request.session.pop('form_data_lists', {})
        context = {
            "preview_ticket_number": _next_ticket_number(),
            "today": timezone.localdate(),
            "branches": Branch.objects.filter(is_active=True).order_by("name"),
            "partners": Contact.objects.order_by("name")[:300],
            "form_data": form_data,
            "form_data_lists": form_data_lists,
        }
        return render(request, self.template_name, context)


class ServiceCheckinSaveView(View):
    def post(self, request):
        def _handle_error(msg):
            messages.error(request, msg)
            request.session['form_data'] = request.POST.dict()
            request.session['form_data_lists'] = {
                'completeness': request.POST.getlist('completeness'),
                'condition': request.POST.getlist('condition')
            }
            return redirect("service:service_checkin")

        branch_id = _parse_int(request.POST.get("branch_id") or request.POST.get("branch"))
        branch = Branch.objects.filter(pk=branch_id).first() if branch_id else None
        customer = _parse_contact_from_partner_input(request.POST.get("partner_id"))

        if not branch:
            return _handle_error("Branch wajib dipilih.")
        if not customer:
            return _handle_error("Customer wajib dipilih.")

        checkin_date = _parse_date(request.POST.get("checkin_date")) or timezone.localdate()
        device_name = str(request.POST.get("device_name") or "").strip().capitalize()
        complaint = (request.POST.get("complaint") or "").strip()
        if not device_name or not complaint:
            return _handle_error("Device name dan complaint wajib diisi.")

        completeness = request.POST.getlist("completeness")
        condition = request.POST.getlist("condition")

        customer_agreement = bool(request.POST.get("customer_agreement"))

        action = (request.POST.get("action") or "save").strip()

        for _ in range(3):
            try:
                with transaction.atomic():
                    ticket_number = _next_ticket_number()
                    ticket = ServiceTicket.objects.create(
                        ticket_number=ticket_number,
                        customer=customer,
                        branch=branch,
                        checkin_date=checkin_date,
                        device_type=(request.POST.get(
                            "device_type") or "").strip(),
                        device_brand=str(request.POST.get(
                            "device_brand") or "").strip().upper(),
                        device_name=device_name,
                        serial_number=(request.POST.get(
                            "serial_number") or "").strip(),
                        device_color=(request.POST.get(
                            "device_color") or "").strip(),
                        completeness=completeness,
                        completeness_notes=(request.POST.get(
                            "completeness_notes") or "").strip(),
                        condition=condition,
                        complaint=complaint,
                        customer_agreement=customer_agreement,
                        created_by=request.user if getattr(
                            request.user, "is_authenticated", False) else None,
                    )

                    header = TransactionHeader.objects.create(
                        invoice_number=f"INV-{ticket_number}",
                        branch=branch,
                        contact=customer,
                        trx_type="SALE",
                        payment_method="CASH",
                        total_amount=Decimal("0"),
                        amount_paid=Decimal("0"),
                        is_finalized=False,
                        created_by=request.user if getattr(
                            request.user, "is_authenticated", False) else None,
                    )
                    ticket.transaction = header
                    ticket.save(update_fields=["transaction"])

                messages.success(request, f"Check-in saved: {ticket_number}")
                if action == "save_print":
                    return redirect("service:service_receipt_usb_print", pk=ticket.pk)
                return redirect("service:service_detail", pk=ticket.pk)
            except IntegrityError:
                continue

        return _handle_error("Gagal membuat ticket. Silakan coba lagi.")


class ServiceExportView(View):
    def get(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="service_tickets.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "ticket_number",
                "status",
                "checkin_date",
                "customer",
                "whatsapp",
                "device",
                "serial_number",
                "branch",
            ]
        )

        qs = ServiceTicket.objects.select_related(
            "customer", "branch").order_by("-id")
        for t in qs[:5000]:
            writer.writerow(
                [
                    t.ticket_number,
                    t.status,
                    t.checkin_date,
                    t.customer.name if t.customer_id else "",
                    t.customer.whatsapp if t.customer_id else "",
                    t.device_name,
                    t.serial_number,
                    t.branch.name if t.branch_id else "",
                ]
            )
        return response


class ServiceDetailView(View):
    def get(self, request, pk):
        ticket = get_object_or_404(
            ServiceTicket.objects.select_related(
                "customer", "branch", "transaction"),
            pk=pk,
        )
        header = ticket.transaction

        ui = STATUS_UI.get(ticket.status, {
                           "label": ticket.status, "badge": "badge-received", "dot": "bg-slate-400"})
        setattr(ticket, "status_label", ui["label"])
        setattr(ticket, "status_badge", ui["badge"])
        setattr(ticket, "status_dot", ui["dot"])

        context = {
            "ticket": ticket,
            "header": header,
        }
        return render(request, "service/service_detail.html", context)


class ServiceCheckinEditView(View):
    def get(self, request, pk):
        ticket = get_object_or_404(ServiceTicket.objects.select_related("customer", "branch"), pk=pk)
        
        form_data = request.session.pop('form_data', {
            'branch': str(ticket.branch_id),
            'partner_id': str(ticket.customer_id),
            'checkin_date': ticket.checkin_date.isoformat() if ticket.checkin_date else '',
            'device_type': ticket.device_type,
            'device_brand': ticket.device_brand,
            'device_name': ticket.device_name,
            'serial_number': ticket.serial_number,
            'device_color': ticket.device_color,
            'completeness_notes': ticket.completeness_notes,
            'complaint': ticket.complaint,
            'customer_agreement': 'on' if ticket.customer_agreement else '',
        })
        form_data_lists = request.session.pop('form_data_lists', {
            'completeness': ticket.completeness,
            'condition': ticket.condition,
        })
        
        context = {
            "ticket": ticket,
            "today": timezone.localdate(),
            "branches": Branch.objects.filter(is_active=True).order_by("name"),
            "partners": Contact.objects.order_by("name")[:300],
            "form_data": form_data,
            "form_data_lists": form_data_lists,
        }
        return render(request, "service/service_checkin.html", context)

    def post(self, request, pk):
        ticket = get_object_or_404(ServiceTicket.objects.select_related("transaction"), pk=pk)
        
        def _handle_error(msg):
            messages.error(request, msg)
            request.session['form_data'] = request.POST.dict()
            request.session['form_data_lists'] = {
                'completeness': request.POST.getlist('completeness'),
                'condition': request.POST.getlist('condition')
            }
            return redirect("service:service_checkin_edit", pk=ticket.pk)

        branch_id = _parse_int(request.POST.get("branch_id") or request.POST.get("branch"))
        branch = Branch.objects.filter(pk=branch_id).first() if branch_id else None
        customer = _parse_contact_from_partner_input(request.POST.get("partner_id"))

        if not branch or not customer:
            return _handle_error("Branch dan Customer wajib dipilih.")

        ticket.branch = branch
        ticket.customer = customer
        ticket.checkin_date = _parse_date(
            request.POST.get("checkin_date")) or ticket.checkin_date
        ticket.device_type = (request.POST.get("device_type") or "").strip()
        ticket.device_brand = (request.POST.get("device_brand") or "").strip()
        ticket.device_name = (request.POST.get(
            "device_name") or "").strip() or ticket.device_name
        ticket.serial_number = (request.POST.get(
            "serial_number") or "").strip()
        ticket.device_color = (request.POST.get("device_color") or "").strip()
        ticket.completeness = request.POST.getlist("completeness")
        ticket.completeness_notes = (request.POST.get(
            "completeness_notes") or "").strip()
        ticket.condition = request.POST.getlist("condition")
        ticket.complaint = (request.POST.get("complaint")
                            or "").strip() or ticket.complaint
        ticket.customer_agreement = bool(
            request.POST.get("customer_agreement"))

        ticket.save()

        if ticket.transaction_id:
            TransactionHeader.objects.filter(pk=ticket.transaction_id).update(
                branch=branch,
                contact=customer,
            )

        messages.success(request, "Check-in updated.")
        return redirect("service:service_detail", pk=ticket.pk)


class ServicePrintTagView(View):
    def get(self, request, pk):
        ticket = get_object_or_404(ServiceTicket.objects.select_related(
            "customer", "branch"), pk=pk)
        return render(request, "service/service_tag_print.html", {"ticket": ticket})


def _print_usb_receipt(request, payload, label):
    printer = WindowsUsbEscposPrinter()
    result = printer.send(payload)
    messages.success(
        request,
        f"{label} terkirim ke printer USB: {result.printer_name}.",
    )


class ServiceIntakeUsbPrintView(View):
    def get(self, request, pk):
        ticket = get_object_or_404(
            ServiceTicket.objects.select_related("customer", "branch"), pk=pk
        )
        payload = EscposBuilder().build_service_intake_receipt(ticket)
        _print_usb_receipt(
            request,
            payload,
            f"Tanda terima servis {ticket.ticket_number}",
        )
        return redirect("service:service_detail", pk=ticket.pk)


class ServiceInvoiceUsbPrintView(View):
    def get(self, request, pk):
        ticket = get_object_or_404(
            ServiceTicket.objects.select_related("customer", "branch", "transaction"), pk=pk
        )
        if not ticket.transaction:
            messages.error(request, "Invoice servis belum tersedia.")
            return redirect("service:service_billing", pk=ticket.pk)

        payload = EscposBuilder().build_service_invoice(ticket, ticket.transaction)
        _print_usb_receipt(
            request,
            payload,
            f"Invoice servis {ticket.transaction.invoice_number}",
        )
        return redirect("service:service_billing", pk=ticket.pk)


class ServiceBillingView(View):
    def get(self, request, pk):
        ticket = get_object_or_404(ServiceTicket.objects.select_related(
            "customer", "branch", "transaction"), pk=pk)
        header = ticket.transaction

        form_data = request.session.pop('form_data', {})

        # Total is stored directly on header (no line items for service)
        subtotal = header.total_amount if header else Decimal("0")
        discount = ticket.discount_amount or Decimal("0")
        grand_total = subtotal - discount
        if grand_total < 0:
            grand_total = Decimal("0")

        amount_paid = header.amount_paid if header else Decimal("0")
        amount_paid_default = amount_paid if amount_paid > 0 else grand_total
        change_amount = amount_paid - grand_total
        if change_amount < 0:
            change_amount = Decimal("0")
        credit_remaining = grand_total - amount_paid
        if credit_remaining < 0:
            credit_remaining = Decimal("0")

        payment_method = getattr(header, "payment_method", "CASH") or "CASH"
        is_credit = payment_method == "CREDIT"

        context = {
            "ticket": ticket,
            "header": header,
            "subtotal": subtotal,
            "discount": discount,
            "grand_total": grand_total,
            "amount_paid_default": amount_paid_default,
            "change_amount": change_amount,
            "credit_remaining": credit_remaining,
            "payment_method": payment_method,
            "is_credit": is_credit,
            "accounts": FinancialAccount.objects.filter(account_type__in=['CASH', 'BANK'], is_active=True).order_by('name'),
            "form_data": form_data,
        }
        return render(request, "service/service_billing.html", context)


class ServiceUpdateStatusView(View):
    def post(self, request, pk):
        ticket = get_object_or_404(ServiceTicket, pk=pk)
        raw = (request.POST.get("status") or "").strip()
        status_map = {
            "received": "RECEIVED",
            "diagnosing": "DIAGNOSING",
            "waiting_parts": "WAITING",
            "waiting": "WAITING",
            "repairing": "REPAIRING",
            "ready": "DONE",
            "done": "DONE",
            "picked": "PICKED",
            "cancelled": "CANCELLED",
            "canceled": "CANCELLED",
        }
        status = status_map.get(raw.lower(), raw.upper())
        valid_status = {s for s, _ in ServiceTicket.STATUS_CHOICES}
        if status not in valid_status:
            messages.error(request, "Status tidak valid.")
            return redirect("service:service_detail", pk=ticket.pk)
        ticket.status = status

        ticket.save(update_fields=["status", "updated_at"])
        messages.success(request, "Status updated.")
        return redirect("service:service_detail", pk=ticket.pk)


class ServiceFinalizeView(View):
    def post(self, request, pk):
        ticket = get_object_or_404(
            ServiceTicket.objects.select_related("transaction"), pk=pk)
        header = ticket.transaction
        
        def _handle_error(msg):
            messages.error(request, msg)
            request.session['form_data'] = request.POST.dict()
            return redirect("service:service_billing", pk=ticket.pk)
            
        if not header:
            return _handle_error("Ticket belum punya transaksi.")

        action = (request.POST.get("action") or "finalize").strip()

        # Service cost is a single total amount
        service_cost = _as_decimal(
            request.POST.get("service_cost"), Decimal("0"))
        discount = _as_decimal(request.POST.get(
            "discount"), ticket.discount_amount or Decimal("0"))
        warranty_days = _parse_int(request.POST.get("warranty_days")) or 0
        invoice_notes = (request.POST.get("invoice_notes") or "").strip()

        payment_method_ui = (request.POST.get(
            "payment_method") or "cash").strip().lower()
        is_credit = bool(request.POST.get("is_credit")
                         ) or payment_method_ui == "credit"

        amount_paid = _as_decimal(
            request.POST.get("amount_paid"), Decimal("0"))
        dp_amount = _as_decimal(request.POST.get("dp_amount"), Decimal("0"))
        due_date = _parse_date(request.POST.get("due_date"))

        ticket.discount_amount = discount
        ticket.warranty_days = max(0, warranty_days)
        ticket.invoice_notes = invoice_notes

        ticket.save(update_fields=[
                    "discount_amount", "warranty_days", "invoice_notes", "updated_at"])

        total_after_discount = service_cost - (discount or Decimal("0"))
        if total_after_discount < 0:
            total_after_discount = Decimal("0")

        header.total_amount = total_after_discount
        header.payment_method = "CREDIT" if is_credit else "CASH"
        header.due_date = due_date if is_credit else None

        actual_paid = dp_amount if is_credit else amount_paid

        if action == "save_draft":
            header.amount_paid = actual_paid
            header.is_finalized = False
            header.save(update_fields=["total_amount", "payment_method",
                        "amount_paid", "due_date", "is_finalized", "updated_at"])
            messages.success(request, "Billing draft saved.")
            return redirect("service:service_billing", pk=ticket.pk)

        # finalize
        if is_credit and not due_date:
            return _handle_error("Due date wajib untuk pembayaran credit.")

        header.is_finalized = True
        header.amount_paid = Decimal("0")  # will be updated by record_payment
        header.save(update_fields=["total_amount", "payment_method",
                    "amount_paid", "due_date", "is_finalized", "updated_at"])

        if actual_paid > 0:
            account_id = request.POST.get("financial_account")
            financial_account = FinancialAccount.objects.filter(
                pk=account_id).first() if account_id else None
            from apps.transaction.services import SalesService
            SalesService.record_payment(header=header, amount=actual_paid,
                                        financial_account=financial_account, note="Pembayaran tagihan service.")

        # Move ticket to ready for pickup
        ticket.status = "DONE"
        ticket.save(update_fields=["status", "updated_at"])

        messages.success(request, "Service finalized & billed.")
        return redirect("service:service_queue")
