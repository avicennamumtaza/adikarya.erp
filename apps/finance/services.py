import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.db import models

from apps.finance.models import FinancialAccount, FinancialTransaction, FinanceCategory

logger = logging.getLogger(__name__)

class FinanceService:
    
    @staticmethod
    @transaction.atomic
    def create_transaction(trx_type, amount, date=None, source_account=None, destination_account=None, 
                           fee=Decimal('0'), reference_number=None, category=None, ref_invoice=None, note=''):
        """
        Core service to create financial transaction and update balances atomically.
        """
        amount = Decimal(str(amount))
        fee = Decimal(str(fee))
        
        if amount <= 0:
            raise ValueError("Amount must be greater than zero.")
            
        if trx_type == 'IN':
            if not destination_account:
                raise ValueError("Destination account is required for IN transactions.")
            
            # Select for update to lock the row and prevent race conditions
            dest = FinancialAccount.objects.select_for_update().get(pk=destination_account.pk)
            dest.balance += amount
            dest.save(update_fields=['balance'])
            destination_account.balance = dest.balance # Update object reference
            
        elif trx_type == 'OUT':
            if not source_account:
                raise ValueError("Source account is required for OUT transactions.")
                
            src = FinancialAccount.objects.select_for_update().get(pk=source_account.pk)
            
            # Safety check
            if src.balance < (amount + fee) and src.account_type not in ['EQUITY', 'LIABILITY']:
                logger.warning(f"Insufficient balance in {src.name}. Proceeding anyway or handle strictly?")
                raise ValueError(f"Insufficient balance in {src.name}.")
                
            src.balance -= (amount + fee)
            src.save(update_fields=['balance'])
            source_account.balance = src.balance
            
        elif trx_type == 'TRANSFER':
            if not source_account or not destination_account:
                raise ValueError("Both source and destination accounts are required for TRANSFER transactions.")
                
            src = FinancialAccount.objects.select_for_update().get(pk=source_account.pk)
            dest = FinancialAccount.objects.select_for_update().get(pk=destination_account.pk)
            
            if src.balance < (amount + fee) and src.account_type not in ['EQUITY', 'LIABILITY']:
                logger.warning(f"Insufficient balance in {src.name} for transfer.")
                raise ValueError(f"Insufficient balance in {src.name}.")
                
            src.balance -= (amount + fee)
            src.save(update_fields=['balance'])
            source_account.balance = src.balance
            
            dest.balance += amount
            dest.save(update_fields=['balance'])
            destination_account.balance = dest.balance
            
        else:
            raise ValueError(f"Invalid transaction type: {trx_type}")

        # Create the transaction record
        trx = FinancialTransaction.objects.create(
            transaction_type=trx_type,
            source_account=source_account,
            destination_account=destination_account,
            amount=amount,
            fee=fee,
            reference_number=reference_number,
            category=category,
            ref_invoice=ref_invoice,
            date=date or timezone.now(),
            note=note
        )
        return trx

    @staticmethod
    @transaction.atomic
    def pay_payable(invoice, amount, source_account, fee=Decimal('0'), note=''):
        """Pembayaran Pembelian / Hutang"""
        amount = Decimal(str(amount))
        
        category_name = 'Pembelian'
        if invoice and invoice.trx_type == 'PURCHASE':
            category_name = 'Pembelian'
            
        category, _ = FinanceCategory.objects.get_or_create(
            name=category_name, category_type='EXPENSE'
        )
        trx = FinanceService.create_transaction(
            trx_type='OUT',
            amount=amount,
            source_account=source_account,
            fee=fee,
            category=category,
            ref_invoice=invoice,
            note=note or f"Pelunasan hutang untuk invoice {invoice.invoice_number}"
        )
        
        # update invoice amount paid
        invoice.amount_paid += amount
        invoice.save(update_fields=['amount_paid'])
        
        # Update contact balance (hutang berkurang -> nilai negatif bertambah mendekati 0)
        # Asumsi: contact.current_balance < 0 untuk hutang
        contact = invoice.contact
        contact.current_balance += amount
        contact.save(update_fields=['current_balance'])
        
        return trx

    @staticmethod
    @transaction.atomic
    def receive_receivable(invoice, amount, destination_account, fee=Decimal('0'), note=''):
        """Penerimaan Penjualan / Piutang / Servis"""
        amount = Decimal(str(amount))
        
        category_name = 'Penjualan'
        if invoice:
            if 'SRV' in invoice.invoice_number:
                category_name = 'Pendapatan Servis'
            elif invoice.trx_type == 'SALE':
                category_name = 'Penjualan'
                
        category, _ = FinanceCategory.objects.get_or_create(
            name=category_name, category_type='INCOME'
        )
        trx = FinanceService.create_transaction(
            trx_type='IN',
            amount=amount,
            destination_account=destination_account,
            fee=fee,
            category=category,
            ref_invoice=invoice,
            note=note or f"Penerimaan piutang untuk invoice {invoice.invoice_number}"
        )
        
        # update invoice amount paid
        invoice.amount_paid += amount
        invoice.save(update_fields=['amount_paid'])
        
        # Update contact balance (piutang berkurang)
        # Asumsi: contact.current_balance > 0 untuk piutang
        contact = invoice.contact
        contact.current_balance -= amount
        contact.save(update_fields=['current_balance'])
        
        return trx

    @staticmethod
    @transaction.atomic
    def inject_capital(amount, destination_account, note=''):
        """Suntikan Modal"""
        amount = Decimal(str(amount))
        category, _ = FinanceCategory.objects.get_or_create(
            name='Suntikan Modal', category_type='EQUITY'
        )
        return FinanceService.create_transaction(
            trx_type='IN',
            amount=amount,
            destination_account=destination_account,
            category=category,
            note=note or "Suntikan Modal"
        )
        
    @staticmethod
    def get_cash_flow(start_date, end_date):
        transactions = FinancialTransaction.objects.filter(
            date__date__gte=start_date,
            date__date__lte=end_date,
            is_void=False
        ).order_by('date')
        
        inflow = transactions.filter(transaction_type='IN').aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0')
        
        # Transfers don't change net cash unless there's a fee (from external perspective).
        # We only count OUT and TRANSFER fees.
        outflow_fee = transactions.filter(transaction_type='TRANSFER').aggregate(
            total=models.Sum('fee')
        )['total'] or Decimal('0')
        
        true_outflow = transactions.filter(transaction_type='OUT').aggregate(
            total=models.Sum(models.F('amount') + models.F('fee'))
        )['total'] or Decimal('0')
        
        total_outflow = true_outflow + outflow_fee
        
        return {
            'transactions': transactions,
            'total_inflow': inflow,
            'total_outflow': total_outflow,
            'net_cash_flow': inflow - total_outflow
        }

    @staticmethod
    def get_account_summary():
        accounts = FinancialAccount.objects.filter(is_active=True)
        total_cash_bank = accounts.filter(account_type__in=['CASH', 'BANK']).aggregate(
            total=models.Sum('balance')
        )['total'] or Decimal('0')
        
        # Total Hutang & Piutang (Assuming apps.partner is available)
        try:
            from apps.partner.models import Contact
            total_payable = Contact.objects.filter(current_balance__lt=0).aggregate(
                total=models.Sum('current_balance')
            )['total'] or Decimal('0')
            
            total_receivable = Contact.objects.filter(current_balance__gt=0).aggregate(
                total=models.Sum('current_balance')
            )['total'] or Decimal('0')
            
            net_worth = total_cash_bank + total_receivable - abs(total_payable)
        except ImportError:
            total_payable = Decimal('0')
            total_receivable = Decimal('0')
            net_worth = total_cash_bank
            
        return {
            'accounts': accounts,
            'total_cash_bank': total_cash_bank,
            'total_payable': abs(total_payable),
            'total_receivable': total_receivable,
            'net_worth': net_worth
        }
