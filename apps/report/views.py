import json
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, F
from django.views.generic import TemplateView
from django.views import View
from django.db import transaction
from django.shortcuts import redirect
from django.contrib import messages

from apps.finance.models import FinancialAccount, FinancialTransaction, FinanceCategory
from apps.transaction.models import TransactionHeader, TransactionDetail
from apps.partner.models import Contact
from apps.inventory.models import Product
from apps.service.models import ServiceTicket

from . import excel_service

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

class ReportDashboardView(TemplateView):
    template_name = 'report/report_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        
        # 1. Total Kas
        accounts = FinancialAccount.objects.filter(is_active=True, account_type__in=['CASH', 'BANK'])
        total_kas = accounts.aggregate(total=Sum('balance'))['total'] or Decimal('0')
        
        # 2. Laba Bersih Bulan Ini (Pendapatan - Beban)
        inflow_month = FinancialTransaction.objects.filter(
            date__date__gte=start_of_month,
            date__date__lte=today,
            category__category_type='INCOME',
            is_void=False
        ).aggregate(t=Sum('amount'))['t'] or Decimal('0')
        
        outflow_month = FinancialTransaction.objects.filter(
            date__date__gte=start_of_month,
            date__date__lte=today,
            category__category_type='EXPENSE',
            is_void=False
        ).aggregate(t=Sum('amount'))['t'] or Decimal('0')
        
        laba_bersih = inflow_month - outflow_month
        
        # 3. Arus Kas Bersih (Total Masuk - Total Keluar bulan ini)
        cash_in = FinancialTransaction.objects.filter(
            date__date__gte=start_of_month,
            date__date__lte=today,
            transaction_type='IN',
            is_void=False
        ).aggregate(t=Sum('amount'))['t'] or Decimal('0')
        
        cash_out = FinancialTransaction.objects.filter(
            date__date__gte=start_of_month,
            date__date__lte=today,
            transaction_type='OUT',
            is_void=False
        ).aggregate(t=Sum(F('amount') + F('fee')))['t'] or Decimal('0')
        
        arus_kas = cash_in - cash_out
        
        # 4. Total Tagihan Overdue
        overdue_sales = TransactionHeader.objects.filter(
            trx_type='SALE',
            payment_method='CREDIT',
            due_date__lt=today,
            is_finalized=True
        ).annotate(
            sisa=F('total_amount') - F('amount_paid')
        ).filter(sisa__gt=0).aggregate(t=Sum('sisa'))['t'] or Decimal('0')
        
        overdue_purchases = TransactionHeader.objects.filter(
            trx_type='PURCHASE',
            payment_method='CREDIT',
            due_date__lt=today,
            is_finalized=True
        ).annotate(
            sisa=F('total_amount') - F('amount_paid')
        ).filter(sisa__gt=0).aggregate(t=Sum('sisa'))['t'] or Decimal('0')
        
        total_overdue = overdue_sales + overdue_purchases
        
        # Trend 6 bulan terakhir
        trend_labels = []
        trend_income = []
        trend_expense = []
        
        for i in range(5, -1, -1):
            m = (today.replace(day=1) - timedelta(days=28 * i)).replace(day=1)
            next_m = (m + timedelta(days=32)).replace(day=1)
            
            inc = FinancialTransaction.objects.filter(
                date__date__gte=m,
                date__date__lt=next_m,
                category__category_type='INCOME',
                is_void=False
            ).aggregate(t=Sum('amount'))['t'] or Decimal('0')
            
            exp = FinancialTransaction.objects.filter(
                date__date__gte=m,
                date__date__lt=next_m,
                category__category_type='EXPENSE',
                is_void=False
            ).aggregate(t=Sum('amount'))['t'] or Decimal('0')
            
            trend_labels.append(m.strftime('%b %Y'))
            trend_income.append(int(inc))
            trend_expense.append(int(exp))
            
        context.update({
            'total_kas': _normalize_money(total_kas),
            'laba_bersih': _normalize_money(laba_bersih),
            'arus_kas': _normalize_money(arus_kas),
            'total_overdue': _normalize_money(total_overdue),
            'trend_labels': json.dumps(trend_labels),
            'trend_income': json.dumps(trend_income),
            'trend_expense': json.dumps(trend_expense),
        })
        return context

class ReportDetailView(TemplateView):
    template_name = 'report/report_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
    
        # Filter tanggal
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if not start_date: start_date = start_of_month.isoformat()
        if not end_date: end_date = today.isoformat()
        
        # TAB A: Cash Flow
        transactions = FinancialTransaction.objects.filter(
            date__date__gte=start_date,
            date__date__lte=end_date,
            is_void=False
        )
        cf_inflow = transactions.filter(transaction_type='IN').aggregate(t=Sum('amount'))['t'] or Decimal('0')
        cf_outflow = transactions.filter(transaction_type='OUT').aggregate(t=Sum(F('amount') + F('fee')))['t'] or Decimal('0')
        
        # TAB B: P&L
        pl_revenue = transactions.filter(category__category_type='INCOME').aggregate(t=Sum('amount'))['t'] or Decimal('0')
        pl_cogs = Decimal('0') # Asumsi HPP jika ada (disini kita aggregate EXPENSE jadi satu)
        pl_expense = transactions.filter(category__category_type='EXPENSE').aggregate(t=Sum('amount'))['t'] or Decimal('0')
        pl_gross = pl_revenue - pl_cogs
        pl_net = pl_gross - pl_expense
        
        # TAB C: Balance Sheet
        bs_kas = FinancialAccount.objects.filter(account_type__in=['CASH', 'BANK']).aggregate(t=Sum('balance'))['t'] or Decimal('0')
        bs_piutang = Contact.objects.filter(current_balance__gt=0).aggregate(t=Sum('current_balance'))['t'] or Decimal('0')
        bs_aset = bs_kas + bs_piutang
        
        bs_hutang = Contact.objects.filter(current_balance__lt=0).aggregate(t=Sum('current_balance'))['t'] or Decimal('0')
        bs_hutang = abs(bs_hutang)
        bs_modal = FinancialAccount.objects.filter(account_type='EQUITY').aggregate(t=Sum('balance'))['t'] or Decimal('0')
        bs_kewajiban_ekuitas = bs_hutang + bs_modal + pl_net # ditambah laba ditahan (mock)
        
        # TAB D: AR/AP
        ar_ap = TransactionHeader.objects.filter(
            payment_method='CREDIT',
            is_finalized=True
        ).annotate(sisa=F('total_amount') - F('amount_paid')).filter(sisa__gt=0)
        
        ar_ap_list = []
        age_0_30 = age_31_60 = age_61_plus = Decimal('0')
        
        for trx in ar_ap:
            age_days = (today - trx.due_date).days if trx.due_date else 0
            sisa = trx.total_amount - trx.amount_paid
            
            if age_days > 60: age_61_plus += sisa
            elif age_days > 30: age_31_60 += sisa
            else: age_0_30 += sisa
            
            ar_ap_list.append({
                'contact': trx.contact.name if trx.contact else '-',
                'type': trx.trx_type,
                'invoice': trx.invoice_number,
                'due_date': trx.due_date,
                'age': age_days,
                'sisa': _normalize_money(sisa)
            })
            
        # normalisasi transaksi di template (amount dan fee)
        for t in transactions:
            t.amount = _normalize_money(t.amount)
            t.fee = _normalize_money(t.fee)

        context.update({
            'start_date': start_date,
            'end_date': end_date,
            'cf_inflow': _normalize_money(cf_inflow),
            'cf_outflow': _normalize_money(cf_outflow),
            'transactions': transactions.order_by('-date')[:50],
            'pl_revenue': _normalize_money(pl_revenue),
            'pl_cogs': _normalize_money(pl_cogs),
            'pl_gross': _normalize_money(pl_gross),
            'pl_expense': _normalize_money(pl_expense),
            'pl_net': _normalize_money(pl_net),
            'bs_kas': _normalize_money(bs_kas),
            'bs_piutang': _normalize_money(bs_piutang),
            'bs_aset': _normalize_money(bs_aset),
            'bs_hutang': _normalize_money(bs_hutang),
            'bs_modal': _normalize_money(bs_modal),
            'bs_kewajiban_ekuitas': _normalize_money(bs_kewajiban_ekuitas),
            'age_0_30': _normalize_money(age_0_30),
            'age_31_60': _normalize_money(age_31_60),
            'age_61_plus': _normalize_money(age_61_plus),
            'ar_ap_list': ar_ap_list,
        })
        return context


# ═══════════════════════════════════════════════════════════════════
#  ANALYTICS DASHBOARD — KPIs & Charts
# ═══════════════════════════════════════════════════════════════════

class AnalyticsDashboardView(TemplateView):
    template_name = 'report/analytics_dashboard.html'

    def get_period_dates(self):
        today = timezone.now().date()
        period = self.request.GET.get('period', '30d')

        if period == 'custom':
            start_str = self.request.GET.get('start_date', '')
            end_str = self.request.GET.get('end_date', '')
            try:
                sd = timezone.datetime.strptime(start_str, '%Y-%m-%d').date() if start_str else today - timedelta(days=30)
                ed = timezone.datetime.strptime(end_str, '%Y-%m-%d').date() if end_str else today
            except (ValueError, TypeError):
                sd, ed = today - timedelta(days=30), today
            days = (ed - sd).days or 30
            prev_sd = sd - timedelta(days=days)
            prev_ed = sd - timedelta(days=1)
            return sd, ed, prev_sd, prev_ed, period

        ranges = {'7d': 7, '30d': 30, 'quarter': 90, 'year': 365}
        days = ranges.get(period, 30)
        sd = today - timedelta(days=days - 1)
        ed = today
        prev_sd = sd - timedelta(days=days)
        prev_ed = sd - timedelta(days=1)
        return sd, ed, prev_sd, prev_ed, period

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        req = self.request
        today = timezone.now().date()
        sd, ed, psd, ped, period = self.get_period_dates()

        ctx = {}
        ctx['period'] = period
        ctx['start_date'] = sd.isoformat()
        ctx['end_date'] = ed.isoformat()
        ctx['today_iso'] = today.isoformat()

        # ── Helper: scalar sum ──
        def _sum(qs, field='amount'):
            v = qs.aggregate(t=Sum(field))['t'] or Decimal('0')
            return int(v)

        def _cnt(qs):
            return qs.count()

        # ═══════════════════════════════════════════════════════
        #  KPI CARDS  (current vs prev period)
        # ═══════════════════════════════════════════════════════

        # 1. Total Revenue — finalized sales
        cur_sales = TransactionHeader.objects.filter(
            trx_type='SALE', is_finalized=True,
            created_at__date__gte=sd, created_at__date__lte=ed)
        prev_sales = TransactionHeader.objects.filter(
            trx_type='SALE', is_finalized=True,
            created_at__date__gte=psd, created_at__date__lte=ped)
        cur_rev = _sum(cur_sales, 'total_amount')
        prev_rev = _sum(prev_sales, 'total_amount')

        # 2. Sales Orders count
        cur_sales_cnt = _cnt(cur_sales)
        prev_sales_cnt = _cnt(prev_sales)

        # 3. Purchase Orders
        cur_pur = TransactionHeader.objects.filter(
            trx_type='PURCHASE', is_finalized=True,
            created_at__date__gte=sd, created_at__date__lte=ed)
        prev_pur = TransactionHeader.objects.filter(
            trx_type='PURCHASE', is_finalized=True,
            created_at__date__gte=psd, created_at__date__lte=ped)
        cur_pur_cnt = _cnt(cur_pur)
        prev_pur_cnt = _cnt(prev_pur)

        # 4. Service Requests — active (not picked / cancelled)
        cur_svc = ServiceTicket.objects.filter(
            created_at__date__gte=sd, created_at__date__lte=ed
        ).exclude(status__in=['PICKED', 'CANCELLED'])
        prev_svc = ServiceTicket.objects.filter(
            created_at__date__gte=psd, created_at__date__lte=ped
        ).exclude(status__in=['PICKED', 'CANCELLED'])
        cur_svc_cnt = _cnt(cur_svc)
        prev_svc_cnt = _cnt(prev_svc)

        # 5. Product Count & in-stock %
        total_products = Product.objects.count()
        from apps.inventory.models import Stock
        in_stock_products = Stock.objects.filter(quantity__gt=0).values('product').distinct().count()
        in_stock_pct = round((in_stock_products / total_products * 100)) if total_products else 0

        # 6. Average Order Value
        cur_aov = _sum(cur_sales, 'total_amount') / cur_sales_cnt if cur_sales_cnt else 0
        prev_aov = _sum(prev_sales, 'total_amount') / prev_sales_cnt if prev_sales_cnt else 0

        # 7. Customer Count — new customers
        cur_cust = Contact.objects.filter(
            contact_type__in=['CUSTOMER', 'BOTH'],
            created_at__date__gte=sd, created_at__date__lte=ed)
        prev_cust = Contact.objects.filter(
            contact_type__in=['CUSTOMER', 'BOTH'],
            created_at__date__gte=psd, created_at__date__lte=ped)
        cur_new_cust = _cnt(cur_cust)
        prev_new_cust = _cnt(prev_cust)
        total_customers = Contact.objects.filter(contact_type__in=['CUSTOMER', 'BOTH']).count()

        # 8. Outstanding Receivables
        cur_recv = TransactionHeader.objects.filter(
            trx_type='SALE', payment_method='CREDIT', is_finalized=True,
            created_at__date__gte=sd, created_at__date__lte=ed
        ).annotate(sisa=F('total_amount') - F('amount_paid')).filter(sisa__gt=0)
        cur_recv_total = 0
        for t in cur_recv:
            cur_recv_total += int(t.sisa)
        prev_recv = TransactionHeader.objects.filter(
            trx_type='SALE', payment_method='CREDIT', is_finalized=True,
            created_at__date__gte=psd, created_at__date__lte=ped
        ).annotate(sisa=F('total_amount') - F('amount_paid')).filter(sisa__gt=0)
        prev_recv_total = 0
        for t in prev_recv:
            prev_recv_total += int(t.sisa)

        # Compute % change helper
        def pct_change(cur, prev):
            if prev == 0:
                return 100.0 if cur > 0 else 0.0
            return round((cur - prev) / prev * 100, 1)

        ctx['kpi'] = {
            'revenue': {'cur': cur_rev, 'prev': prev_rev, 'pct': pct_change(cur_rev, prev_rev)},
            'sales_orders': {'cur': cur_sales_cnt, 'prev': prev_sales_cnt, 'pct': pct_change(cur_sales_cnt, prev_sales_cnt)},
            'purchase_orders': {'cur': cur_pur_cnt, 'prev': prev_pur_cnt, 'pct': pct_change(cur_pur_cnt, prev_pur_cnt)},
            'service_requests': {'cur': cur_svc_cnt, 'prev': prev_svc_cnt, 'pct': pct_change(cur_svc_cnt, prev_svc_cnt)},
            'products': {'cur': total_products, 'in_stock_pct': in_stock_pct},
            'aov': {'cur': round(cur_aov), 'prev': round(prev_aov), 'pct': pct_change(cur_aov, prev_aov)},
            'customers': {'cur': total_customers, 'new': cur_new_cust, 'prev_new': prev_new_cust, 'pct_new': pct_change(cur_new_cust, prev_new_cust)},
            'receivables': {'cur': cur_recv_total, 'prev': prev_recv_total, 'pct': pct_change(cur_recv_total, prev_recv_total)},
        }

        # ═══════════════════════════════════════════════════════
        #  CHART 1A: Revenue Trend (12 months)
        # ═══════════════════════════════════════════════════════
        rev_labels = []
        rev_sales = []
        rev_service = []
        rev_other = []

        for i in range(11, -1, -1):
            m = (today.replace(day=1) - timedelta(days=28 * i)).replace(day=1)
            nm = (m + timedelta(days=32)).replace(day=1)
            rev_labels.append(m.strftime('%b %Y'))

            # Sales revenue from finalized sales transactions
            sales_amt = TransactionHeader.objects.filter(
                trx_type='SALE', is_finalized=True,
                created_at__date__gte=m, created_at__date__lt=nm
            ).aggregate(t=Sum('total_amount'))['t'] or Decimal('0')
            rev_sales.append(int(sales_amt))

            # Service revenue
            svc_ids = ServiceTicket.objects.filter(
                transaction__isnull=False,
                created_at__date__gte=m, created_at__date__lt=nm
            ).values_list('transaction_id', flat=True)
            svc_amt = TransactionHeader.objects.filter(
                id__in=svc_ids, is_finalized=True
            ).aggregate(t=Sum('total_amount'))['t'] or Decimal('0')
            rev_service.append(int(svc_amt))

            # Other = total - sales - service
            total = int(sales_amt + svc_amt)
            # No other_rev for simplicity — just sales + service, other = 0
            rev_other.append(0)

        ctx['chart1a'] = {
            'labels': json.dumps(rev_labels),
            'sales': json.dumps(rev_sales),
            'service': json.dumps(rev_service),
            'other': json.dumps(rev_other),
        }

        # ═══════════════════════════════════════════════════════
        #  CHART 1B: Sales vs Purchases (12 months)
        # ═══════════════════════════════════════════════════════
        bar_labels = []
        bar_sales_amt = []
        bar_pur_amt = []
        bar_sales_cnt = []
        bar_pur_cnt = []

        for i in range(11, -1, -1):
            m = (today.replace(day=1) - timedelta(days=28 * i)).replace(day=1)
            nm = (m + timedelta(days=32)).replace(day=1)
            bar_labels.append(m.strftime('%b'))

            s_amt = TransactionHeader.objects.filter(
                trx_type='SALE', is_finalized=True,
                created_at__date__gte=m, created_at__date__lt=nm
            ).aggregate(t=Sum('total_amount'))['t'] or Decimal('0')

            p_amt = TransactionHeader.objects.filter(
                trx_type='PURCHASE', is_finalized=True,
                created_at__date__gte=m, created_at__date__lt=nm
            ).aggregate(t=Sum('total_amount'))['t'] or Decimal('0')

            s_cnt = TransactionHeader.objects.filter(
                trx_type='SALE', is_finalized=True,
                created_at__date__gte=m, created_at__date__lt=nm
            ).count()

            p_cnt = TransactionHeader.objects.filter(
                trx_type='PURCHASE', is_finalized=True,
                created_at__date__gte=m, created_at__date__lt=nm
            ).count()

            bar_sales_amt.append(int(s_amt))
            bar_pur_amt.append(int(p_amt))
            bar_sales_cnt.append(s_cnt)
            bar_pur_cnt.append(p_cnt)

        ctx['chart1b'] = {
            'labels': json.dumps(bar_labels),
            'sales_amt': json.dumps(bar_sales_amt),
            'purch_amt': json.dumps(bar_pur_amt),
            'sales_cnt': json.dumps(bar_sales_cnt),
            'purch_cnt': json.dumps(bar_pur_cnt),
        }

        # ═══════════════════════════════════════════════════════
        #  CHART 2A: Revenue by Product Category
        # ═══════════════════════════════════════════════════════
        from django.db.models import OuterRef, Subquery
        cat_rev = {}
        for p in Product.objects.exclude(category='').values('category').distinct():
            cat = p['category']
            # Sum of TransactionDetail for products in this category
            amt = TransactionDetail.objects.filter(
                product__category=cat,
                header__is_finalized=True,
                header__trx_type='SALE',
                header__created_at__date__gte=sd,
                header__created_at__date__lte=ed,
            ).aggregate(t=Sum(F('qty') * F('price_at_trx')))['t'] or Decimal('0')
            if int(amt) > 0:
                cat_rev[cat] = int(amt)

        # Sort by value descending, take top 8
        sorted_cats = sorted(cat_rev.items(), key=lambda x: -x[1])
        top_cats = sorted_cats[:8]
        ctx['chart2a'] = {
            'labels': json.dumps([c[0] for c in top_cats]),
            'values': json.dumps([c[1] for c in top_cats]),
        }

        # ═══════════════════════════════════════════════════════
        #  CHART 2B: Payment Status Distribution
        # ═══════════════════════════════════════════════════════
        finalized = TransactionHeader.objects.filter(
            is_finalized=True,
            created_at__date__gte=sd, created_at__date__lte=ed
        )
        paid = finalized.filter(payment_method='CASH').count()
        credit = finalized.filter(payment_method='CREDIT')
        pending = credit.annotate(sisa=F('total_amount') - F('amount_paid')).filter(sisa__gt=0).count()
        overdue = credit.filter(due_date__lt=today).annotate(sisa=F('total_amount') - F('amount_paid')).filter(sisa__gt=0).count()
        paid_count = paid + (finalized.filter(payment_method='CREDIT').count() - pending - overdue)
        cancelled = TransactionHeader.objects.filter(is_finalized=False).count()

        ctx['chart2b'] = {
            'paid': paid_count,
            'pending': max(0, pending - overdue),
            'overdue': overdue,
            'cancelled': cancelled,
            'total': paid_count + max(0, pending - overdue) + overdue + cancelled,
        }

        # ═══════════════════════════════════════════════════════
        #  CHART 2C: Service Request Status
        # ═══════════════════════════════════════════════════════
        svc_all = ServiceTicket.objects.filter(
            created_at__date__gte=sd, created_at__date__lte=ed)
        svc_completed = svc_all.filter(status='DONE').count()
        svc_in_progress = svc_all.filter(status__in=['DIAGNOSING', 'REPAIRING']).count()
        svc_pending = svc_all.filter(status__in=['RECEIVED', 'WAITING']).count()
        svc_total = svc_all.count()
        svc_completion_rate = round(svc_completed / svc_total * 100) if svc_total else 0

        circumference = 377
        dashoffset = round(circumference * (100 - svc_completion_rate) / 100)
        ctx['chart2c'] = {
            'completed': svc_completed,
            'in_progress': svc_in_progress,
            'pending': svc_pending,
            'total': svc_total,
            'rate': svc_completion_rate,
            'dashoffset': dashoffset,
        }

        # ═══════════════════════════════════════════════════════
        #  CHART 3A: Top 10 Products by Sales
        # ═══════════════════════════════════════════════════════
        top_products = []
        top_prod_qs = TransactionDetail.objects.filter(
            header__is_finalized=True,
            header__trx_type='SALE',
            header__created_at__date__gte=sd,
            header__created_at__date__lte=ed,
        ).values('product_id', 'product__name').annotate(
            total_qty=Sum('qty'),
            total_rev=Sum(F('qty') * F('price_at_trx'))
        ).order_by('-total_rev')[:10]

        # Fetch sparkline data per product (last 7 days)
        for i, p in enumerate(top_prod_qs):
            pid = p['product_id']
            spark = []
            for d in range(6, -1, -1):
                day = today - timedelta(days=d)
                q = TransactionDetail.objects.filter(
                    product_id=pid,
                    header__is_finalized=True,
                    header__trx_type='SALE',
                    header__created_at__date=day,
                ).aggregate(t=Sum('qty'))['t'] or 0
                spark.append(int(q))
            top_products.append({
                'rank': i + 1,
                'name': p['product__name'],
                'qty': p['total_qty'],
                'rev': int(p['total_rev']),
                'spark': spark,
            })

        ctx['chart3a'] = top_products
        ctx['chart3a_json'] = json.dumps(top_products)

        # ═══════════════════════════════════════════════════════
        #  CHART 3B: Finance Summary
        # ═══════════════════════════════════════════════════════
        fin_rev = FinancialTransaction.objects.filter(
            date__date__gte=sd, date__date__lte=ed,
            category__category_type='INCOME', is_void=False
        ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

        fin_exp = FinancialTransaction.objects.filter(
            date__date__gte=sd, date__date__lte=ed,
            category__category_type='EXPENSE', is_void=False
        ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

        fin_cogs = Decimal('0')
        # Estimate COGS from purchase costs
        cogs_val = TransactionDetail.objects.filter(
            header__is_finalized=True,
            header__trx_type='SALE',
            header__created_at__date__gte=sd,
            header__created_at__date__lte=ed,
        ).aggregate(t=Sum(F('qty') * F('cost_at_trx')))['t'] or Decimal('0')
        fin_cogs = cogs_val

        fin_profit = int(fin_rev) - int(fin_exp) - int(fin_cogs)

        # Previous period comparison
        prev_fin_rev = FinancialTransaction.objects.filter(
            date__date__gte=psd, date__date__lte=ped,
            category__category_type='INCOME', is_void=False
        ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

        ctx['chart3b'] = {
            'revenue': int(fin_rev),
            'cogs': int(fin_cogs),
            'expense': int(fin_exp),
            'profit': fin_profit,
            'prev_revenue': int(prev_fin_rev),
        }

        context.update(ctx)
        return context


# ═══════════════════════════════════════════════════════════════════
#  DATA HUB — Import / Export Dashboard
# ═══════════════════════════════════════════════════════════════════

class DataHubView(TemplateView):
    template_name = 'report/data_hub.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['product_count'] = Product.objects.count()
        ctx['partner_count'] = Contact.objects.count()
        ctx['sales_count'] = TransactionHeader.objects.filter(trx_type='SALE').count()
        ctx['purchase_count'] = TransactionHeader.objects.filter(trx_type='PURCHASE').count()
        ctx['finance_count'] = FinancialTransaction.objects.count()
        ctx['service_count'] = ServiceTicket.objects.count()
        return ctx


# ── Export Views ──────────────────────────────────────────────────

class ExportProductsView(View):
    def get(self, request):
        return excel_service.export_products(Product.objects.all())

class ExportPartnersView(View):
    def get(self, request):
        return excel_service.export_partners(Contact.objects.all())

class ExportSalesView(View):
    def get(self, request):
        return excel_service.export_sales(
            TransactionHeader.objects.filter(trx_type='SALE').order_by('-created_at'))

class ExportPurchasesView(View):
    def get(self, request):
        return excel_service.export_purchases(
            TransactionHeader.objects.filter(trx_type='PURCHASE').order_by('-created_at'))

class ExportFinanceView(View):
    def get(self, request):
        return excel_service.export_finance(
            FinancialTransaction.objects.all().order_by('-date'))

class ExportServiceView(View):
    def get(self, request):
        return excel_service.export_service(ServiceTicket.objects.all().order_by('-created_at'))


# ── Import Views ──────────────────────────────────────────────────

class _BaseImportView(View):
    """Base class for import views. Subclasses set import_fn and label."""
    import_fn = None
    label = ""

    def get_success_url(self):
        return self.request.POST.get('next') or self.request.GET.get('next') or 'report:data_hub'

    def post(self, request):
        f = request.FILES.get('file')
        if not f:
            messages.error(request, "Tidak ada file yang dipilih.")
            return redirect(self.get_success_url())
        if not f.name.endswith('.xlsx'):
            messages.error(request, "Format file harus .xlsx")
            return redirect(self.get_success_url())
        try:
            (created, second), errors = self.import_fn(f)
            label2 = "dilewati" if "sale" in self.label.lower() or "purchase" in self.label.lower() or "service" in self.label.lower() or "finance" in self.label.lower() else "diperbarui"
            msg = f"Import {self.label} selesai: {created} dibuat, {second} {label2}."
            if errors:
                msg += f" {len(errors)} error."
            messages.success(request, msg)
            if errors:
                for e in errors[:5]:
                    messages.warning(request, e)
        except Exception as e:
            messages.error(request, f"Import gagal: {e}")
        return redirect(self.get_success_url())


class ImportProductsView(_BaseImportView):
    import_fn = staticmethod(excel_service.import_products)
    label = "Produk"

class ImportPartnersView(_BaseImportView):
    import_fn = staticmethod(excel_service.import_partners)
    label = "Partner"

class ImportSalesView(_BaseImportView):
    import_fn = staticmethod(excel_service.import_sales)
    label = "Penjualan"

class ImportPurchasesView(_BaseImportView):
    import_fn = staticmethod(excel_service.import_purchases)
    label = "Pembelian"

class ImportFinanceView(_BaseImportView):
    import_fn = staticmethod(excel_service.import_finance)
    label = "Keuangan"

class ImportServiceView(_BaseImportView):
    import_fn = staticmethod(excel_service.import_service)
    label = "Servis"
