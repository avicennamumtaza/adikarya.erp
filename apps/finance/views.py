from django.shortcuts import render
from django.views.generic import TemplateView, DetailView, FormView
from django.urls import reverse_lazy
from .forms import GeneralTransactionForm
import calendar
from django.utils import timezone
from decimal import Decimal
from .services import FinanceService
from apps.common.escpos_builder import WindowsUsbEscposPrinter
from django.views import View
from django.contrib import messages
from django.shortcuts import redirect
from django.core.paginator import Paginator
from django.db.models import Q, Case, When, Value, CharField

from apps.finance.models import FinancialAccount, FinancialTransaction


def _normalize_money(value):
    if value is None:
        return 0
    if isinstance(value, Decimal):
        from decimal import ROUND_HALF_UP
        return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


class FinanceDashboardView(TemplateView):
    template_name = "finance/dashboard.html"
    ITEMS_PER_PAGE = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request

        # ── Date Range (default: current month) ──
        today = timezone.now().date()
        start_date = today.replace(day=1)
        end_date = today.replace(
            day=calendar.monthrange(today.year, today.month)[1])

        date_from_str = request.GET.get('date_from')
        date_to_str = request.GET.get('date_to')

        if date_from_str:
            try:
                start_date = timezone.datetime.strptime(
                    date_from_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        if date_to_str:
            try:
                end_date = timezone.datetime.strptime(
                    date_to_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        # ── Global Financial Data ──
        cash_flow_data = FinanceService.get_cash_flow(start_date, end_date)
        account_summary = FinanceService.get_account_summary()

        # Normalize money values
        cash_flow_data['total_inflow'] = _normalize_money(cash_flow_data['total_inflow'])
        cash_flow_data['total_outflow'] = _normalize_money(cash_flow_data['total_outflow'])
        cash_flow_data['net_cash_flow'] = _normalize_money(cash_flow_data['net_cash_flow'])

        account_summary['total_cash_bank'] = _normalize_money(account_summary['total_cash_bank'])
        account_summary['total_payable'] = _normalize_money(account_summary['total_payable'])
        account_summary['total_receivable'] = _normalize_money(account_summary['total_receivable'])
        account_summary['net_worth'] = _normalize_money(account_summary['net_worth'])
        for acc in account_summary['accounts']:
            acc.balance = _normalize_money(acc.balance)

        # ── Tab-based Account Logic ──
        accounts = FinancialAccount.objects.filter(is_active=True).order_by('pk')
        active_tab = request.GET.get('tab', '')
        active_account = None
        tab_transactions = None
        tab_stat_inflow = 0
        tab_stat_outflow = 0
        tab_stat_count = 0

        if accounts.exists():
            if active_tab:
                active_account = accounts.filter(pk=active_tab).first()
            if not active_account:
                active_account = accounts.first()
                active_tab = str(active_account.pk)
            else:
                active_tab = str(active_account.pk)

            active_account.balance = _normalize_money(active_account.balance)

            # Build queryset: all non-void transactions related to this account
            qs = FinancialTransaction.objects.filter(
                Q(source_account=active_account) | Q(destination_account=active_account),
                is_void=False,
                date__date__gte=start_date,
                date__date__lte=end_date,
            ).annotate(
                direction=Case(
                    When(destination_account=active_account, then=Value('IN')),
                    When(source_account=active_account, then=Value('OUT')),
                    default=Value('OUT'),
                    output_field=CharField(),
                )
            ).select_related(
                'category', 'ref_invoice', 'ref_invoice__contact',
                'source_account', 'destination_account',
            ).order_by('-date', '-pk')

            # ── Apply Filters ──
            search_q = request.GET.get('q', '').strip()
            if search_q:
                qs = qs.filter(
                    Q(note__icontains=search_q) |
                    Q(reference_number__icontains=search_q) |
                    Q(category__name__icontains=search_q) |
                    Q(ref_invoice__invoice_number__icontains=search_q)
                )

            trx_type_filter = request.GET.get('trx_type', '')
            if trx_type_filter in ('IN', 'OUT', 'TRANSFER'):
                if trx_type_filter == 'IN':
                    qs = qs.filter(destination_account=active_account)
                elif trx_type_filter == 'OUT':
                    qs = qs.filter(source_account=active_account).exclude(
                        transaction_type='TRANSFER', destination_account=active_account
                    )
                else:  # TRANSFER
                    qs = qs.filter(transaction_type='TRANSFER')

            # ── Tab Stats (before pagination) ──
            from django.db.models import Sum
            tab_stat_count = qs.count()

            inflow_qs = qs.filter(direction='IN')
            outflow_qs = qs.filter(direction='OUT')
            tab_stat_inflow = _normalize_money(
                inflow_qs.aggregate(total=Sum('amount'))['total']
            )
            tab_stat_outflow = _normalize_money(
                outflow_qs.aggregate(total=Sum('amount'))['total']
            )

            # ── Pagination ──
            paginator = Paginator(qs, self.ITEMS_PER_PAGE)
            page_number = request.GET.get('page', 1)
            tab_transactions = paginator.get_page(page_number)

            # ── Running Balance Calculation & Normalization ──
            raw_acc = FinancialAccount.objects.get(pk=active_account.pk)
            running_bal = raw_acc.balance
            
            if tab_transactions:
                first_trx = tab_transactions[0]
                newer_qs = FinancialTransaction.objects.filter(
                    Q(source_account=active_account) | Q(destination_account=active_account),
                    is_void=False
                ).filter(
                    Q(date__gt=first_trx.date) | Q(date=first_trx.date, pk__gt=first_trx.pk)
                )
                
                newer_inflow = newer_qs.filter(destination_account=active_account).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                newer_outflow_amt = newer_qs.filter(source_account=active_account).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                newer_outflow_fee = newer_qs.filter(source_account=active_account).aggregate(total=Sum('fee'))['total'] or Decimal('0')
                
                running_bal = running_bal - newer_inflow + newer_outflow_amt + newer_outflow_fee
                
                for trx in tab_transactions:
                    trx.running_balance = _normalize_money(running_bal)
                    
                    if trx.destination_account_id == active_account.pk:
                        running_bal -= trx.amount
                    if trx.source_account_id == active_account.pk:
                        running_bal += (trx.amount + trx.fee)
                        
                    trx.amount = _normalize_money(trx.amount)
                    trx.fee = _normalize_money(trx.fee)

        context.update({
            'start_date': start_date,
            'end_date': end_date,
            'cash_flow_data': cash_flow_data,
            'account_summary': account_summary,
            # Tab data
            'accounts': accounts,
            'active_tab': active_tab,
            'active_account': active_account,
            'tab_transactions': tab_transactions,
            'tab_stat_inflow': tab_stat_inflow,
            'tab_stat_outflow': tab_stat_outflow,
            'tab_stat_count': tab_stat_count,
        })

        return context


class FinanceTransactionDetailView(DetailView):
    """Detail view for a single FinancialTransaction."""
    model = FinancialTransaction
    template_name = "finance/transaction_detail.html"
    context_object_name = "trx"

    def get_queryset(self):
        return FinancialTransaction.objects.select_related(
            'source_account', 'destination_account',
            'category', 'ref_invoice', 'ref_invoice__contact',
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        trx = self.object
        # Normalize for display
        trx.amount = _normalize_money(trx.amount)
        trx.fee = _normalize_money(trx.fee)
        # Preserve the tab the user came from
        context['back_tab'] = self.request.GET.get('tab', '')
        return context


class GeneralTransactionCreateView(FormView):
    template_name = "finance/transaction_form.html"
    form_class = GeneralTransactionForm
    success_url = reverse_lazy('finance:dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Catat Transaksi'
        return context

    def form_valid(self, form):
        try:
            FinanceService.create_transaction(
                trx_type=form.cleaned_data['transaction_type'],
                amount=form.cleaned_data['amount'],
                date=form.cleaned_data['date'],
                source_account=form.cleaned_data['source_account'],
                destination_account=form.cleaned_data['destination_account'],
                fee=form.cleaned_data['fee'],
                category=form.cleaned_data['category'],
                note=form.cleaned_data['note']
            )
            messages.success(self.request, "Transaksi berhasil dicatat.")
            return super().form_valid(form)
        except ValueError as ve:
            messages.error(self.request, str(ve))
            return self.form_invalid(form)
        except Exception as e:
            messages.error(self.request, f"Terjadi kesalahan saat menyimpan transaksi: {str(e)}")
            return self.form_invalid(form)

class PrintExperimentView(View):
    """
    Experimental view to test 80mm ESC/POS printing with dummy data.
    """
    def get(self, request):
        # 1. ESC/POS Command Constants
        ESC = b"\x1b"
        GS = b"\x1d"
        
        CMD_INIT = ESC + b"@"
        CMD_CENTER = ESC + b"a\x01"
        CMD_LEFT = ESC + b"a\x00"
        CMD_RIGHT = ESC + b"a\x02"
        CMD_FONT_A = ESC + b"M\x00"
        CMD_BOLD_ON = ESC + b"E\x01"
        CMD_BOLD_OFF = ESC + b"E\x00"
        CMD_SIZE_LARGE = GS + b"!\x11"  # Double width + Double height
        CMD_SIZE_NORMAL = GS + b"!\x00"
        CMD_CUT = GS + b"V\x41\x03"     # Partial cut with feed
        
        # 2. Helper functions for raw bytes
        def text(s): return s.encode('ascii', 'ignore')
        def line(s=""): return text(s + "\n")
        def money(amt): return f"Rp {int(amt):,}".replace(",", ".")

        # 3. Build Raw Payload
        payload = bytearray()
        payload.extend(CMD_INIT)
        payload.extend(CMD_FONT_A)
        
        # --- Header ---
        payload.extend(CMD_CENTER)
        payload.extend(CMD_SIZE_LARGE)
        payload.extend(CMD_BOLD_ON)
        payload.extend(line("ADIKARYA COMPUTER"))
        payload.extend(CMD_SIZE_NORMAL)
        payload.extend(CMD_BOLD_OFF)
        payload.extend(line("Solusi Komputer & Gadget Anda"))
        payload.extend(line("Jl. Laras Liris No. 30, Lamongan"))
        payload.extend(line("Telp: 0812-3456-7890"))
        
        # --- Divider ---
        payload.extend(CMD_LEFT)
        payload.extend(line("=" * 48))
        
        # --- Transaction Info ---
        payload.extend(CMD_BOLD_ON)
        payload.extend(line("EKSPERIMEN PRINT 80MM".center(48)))
        payload.extend(CMD_BOLD_OFF)
        payload.extend(line())
        
        payload.extend(line(f"No. Nota  : INV/2026/TEST/001"))
        payload.extend(line(f"Tanggal   : {timezone.now().strftime('%d/%m/%Y %H:%M')}"))
        payload.extend(line(f"Kasir     : {request.user.username}"))
        payload.extend(line(f"Pelanggan : Bpk. Budi Santoso (Dummy)"))
        payload.extend(line("-" * 48))
        
        # --- Items ---
        items = [
            ("Keyboard Mechanical RGB", 1, 750000),
            ("Mouse Wireless X1", 2, 250000),
            ("Flashdisk 64GB USB 3.0", 1, 125000),
        ]
        
        total = 0
        for name, qty, price in items:
            sub = qty * price
            total += sub
            # Row 1: Name
            payload.extend(line(name))
            # Row 2: Qty x Price ... Subtotal
            calc = f"  {qty} x {money(price)}"
            val = money(sub)
            gap = 48 - len(calc) - len(val)
            payload.extend(line(f"{calc}{' ' * gap}{val}"))
        
        payload.extend(line("-" * 48))
        
        # --- Totals ---
        def total_row(label, val_str, bold=False):
            if bold: payload.extend(CMD_BOLD_ON)
            gap = 48 - len(label) - len(val_str) - 3 # ' : '
            payload.extend(line(f"{label}{' ' * gap} : {val_str}"))
            if bold: payload.extend(CMD_BOLD_OFF)

        total_row("TOTAL", money(total), bold=True)
        total_row("BAYAR", money(1500000))
        total_row("KEMBALI", money(1500000 - total), bold=True)
        
        # --- Footer ---
        payload.extend(line("=" * 48))
        payload.extend(CMD_CENTER)
        payload.extend(line())
        payload.extend(line("TERIMA KASIH ATAS KUNJUNGAN ANDA"))
        payload.extend(line("Barang yang sudah dibeli tidak dapat"))
        payload.extend(line("ditukar atau dikembalikan."))
        payload.extend(line())
        payload.extend(line("www.adikarya.co"))
        payload.extend(line())
        payload.extend(line())
        
        # --- Cut ---
        payload.extend(CMD_CUT)

        # 4. Send to printer
        printer = WindowsUsbEscposPrinter()
        try:
            result = printer.send(bytes(payload))
            messages.success(request, f"Eksperimen Raw ESC/POS berhasil: {result.printer_name}")
        except Exception as e:
            messages.error(request, f"Gagal cetak manual: {str(e)}")

        return redirect("finance:dashboard")
