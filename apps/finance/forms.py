from django import forms
from django.utils import timezone
from apps.finance.models import FinancialAccount, FinanceCategory, FinancialTransaction


class GeneralTransactionForm(forms.Form):
    transaction_type = forms.ChoiceField(
        choices=FinancialTransaction.TRX_TYPE_CHOICES,
        label="Tipe Transaksi",
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all',
            'x-model': 'trxType'
        })
    )

    date = forms.DateTimeField(
        initial=timezone.now,
        label="Tanggal Transaksi",
        widget=forms.DateTimeInput(
            attrs={'type': 'datetime-local', 'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all'})
    )

    source_account = forms.ModelChoiceField(
        queryset=FinancialAccount.objects.filter(is_active=True),
        required=False,
        label="Akun Sumber (Ditarik Dari)",
        empty_label="-- Pilih Akun Sumber --",
        widget=forms.Select(attrs={
                            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all'})
    )

    destination_account = forms.ModelChoiceField(
        queryset=FinancialAccount.objects.filter(is_active=True),
        required=False,
        label="Akun Tujuan (Disimpan Ke)",
        empty_label="-- Pilih Akun Tujuan --",
        widget=forms.Select(attrs={
                            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all'})
    )

    category = forms.ModelChoiceField(
        queryset=FinanceCategory.objects.all(),
        required=False,
        label="Kategori",
        empty_label="-- Pilih Kategori --",
        widget=forms.Select(attrs={
                            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all'})
    )

    amount = forms.DecimalField(
        max_digits=15, decimal_places=2, min_value=0.01,
        label="Nominal Transaksi (Rp)",
        widget=forms.NumberInput(attrs={
                                 'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all', 'placeholder': '0', 'step': '1'})
    )

    fee = forms.DecimalField(
        max_digits=15, decimal_places=2, min_value=0, required=False, initial=0,
        label="Biaya Admin / Fee (Rp)",
        widget=forms.NumberInput(attrs={
                                 'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all', 'placeholder': '0', 'step': '1'})
    )

    note = forms.CharField(
        required=False,
        label="Catatan / Deskripsi",
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all',
                              'placeholder': 'Misal: Pembayaran pajak bulan ini, renovasi toko, dll'})
    )

    def clean(self):
        cleaned_data = super().clean()
        trx_type = cleaned_data.get('transaction_type')
        source = cleaned_data.get('source_account')
        dest = cleaned_data.get('destination_account')

        if trx_type == 'IN':
            if not dest:
                self.add_error(
                    'destination_account', "Akun tujuan wajib diisi untuk transaksi Pemasukan.")
        elif trx_type == 'OUT':
            if not source:
                self.add_error(
                    'source_account', "Akun sumber wajib diisi untuk transaksi Pengeluaran.")
        elif trx_type == 'TRANSFER':
            if not source:
                self.add_error('source_account',
                               "Akun sumber wajib diisi untuk Transfer.")
            if not dest:
                self.add_error('destination_account',
                               "Akun tujuan wajib diisi untuk Transfer.")
            if source and dest and source == dest:
                self.add_error('destination_account',
                               "Akun sumber dan tujuan tidak boleh sama.")

        return cleaned_data
