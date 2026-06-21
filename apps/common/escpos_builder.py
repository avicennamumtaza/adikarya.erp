from __future__ import annotations

import textwrap
import unicodedata
from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings
from django.utils.timezone import localtime

try:
    import win32print
except ImportError:  # pragma: no cover - handled at runtime if printer action is used.
    win32print = None


@dataclass(frozen=True)
class PrintResult:
    printer_name: str
    bytes_written: int


class WindowsUsbEscposPrinter:
    def __init__(self, printer_name: str | None = None):
        configured_name = (printer_name or getattr(
            settings, "ESC_POS_PRINTER_NAME", "") or "").strip()
        if configured_name:
            self.printer_name = configured_name
        elif win32print is not None:
            self.printer_name = win32print.GetDefaultPrinter()
        else:
            self.printer_name = ""

    def send(self, payload: bytes) -> PrintResult:
        if win32print is None:
            raise RuntimeError(
                "pywin32 is required for USB printing on Windows.")
        if not self.printer_name:
            raise RuntimeError(
                "ESC_POS_PRINTER_NAME is not configured and no default printer is available.")
        if not payload:
            raise ValueError("ESC/POS payload is empty.")

        handle = win32print.OpenPrinter(self.printer_name)
        try:
            job_id = win32print.StartDocPrinter(
                handle, 1, ("Donezo Receipt", None, "RAW"))
            try:
                win32print.StartPagePrinter(handle)
                win32print.WritePrinter(handle, payload)
                win32print.EndPagePrinter(handle)
            finally:
                win32print.EndDocPrinter(handle)
        finally:
            win32print.ClosePrinter(handle)

        return PrintResult(printer_name=self.printer_name, bytes_written=len(payload))


class EscposBuilder:
    def __init__(
        self,
        store_name: str = "ADIKARYA COMPUTER",
        store_address: str = "Jl. Laras Liris 30 Lamongan",
        store_phone: str = "Telp: 0812-3456-7890",
        store_tagline: str = "",
        columns: int = 48,
        footer_note: str = "Terima kasih! Kunjungi kami kembali.",
        reset_on_init: bool = True,
    ):
        self.store_name = store_name
        self.store_address = store_address
        self.store_phone = store_phone
        self.store_tagline = store_tagline
        self.columns = columns
        self.footer_note = footer_note
        self.reset_on_init = bool(reset_on_init)
        self._buffer = bytearray()
        self._initialize()

    def _initialize(self):
        if self.reset_on_init:
            self._buffer.extend(b"\x1b@")
        self._buffer.extend(b"\x1bt\x00")

    def _set_bold(self, enabled: bool):
        self._buffer.extend(b"\x1bE\x01" if enabled else b"\x1bE\x00")

    def _set_align(self, align: str = "left"):
        if align == "center":
            self._buffer.extend(b"\x1ba\x01")
        elif align == "right":
            self._buffer.extend(b"\x1ba\x02")
        else:
            self._buffer.extend(b"\x1ba\x00")

    def _set_size(self, width: int = 1, height: int = 1):
        """Set font size (1-8)"""
        w = max(1, min(8, width)) - 1
        h = max(1, min(8, height)) - 1
        n = (w << 4) | h
        self._buffer.extend(b"\x1d!" + bytes([n]))

    def output(self, trim_initial: bool = False):
        payload = bytes(self._buffer)
        if not trim_initial:
            return payload
        for i, b in enumerate(payload):
            if b == 0x0A or 0x20 <= b <= 0x7E:
                return payload[i:]
        return payload

    def _normalize_text(self, value):
        text = "" if value is None else str(value)
        text = unicodedata.normalize("NFKD", text)
        return text.encode("ascii", "ignore").decode("ascii").replace("\r", "")

    def _line(self, value=""):
        self._buffer.extend(self._normalize_text(
            value).encode("ascii", "replace"))
        self._buffer.extend(b"\n")

    def _feed(self, count=1):
        self._buffer.extend(b"\n" * max(0, int(count)))

    def _rule(self, char="="):
        self._line(char * self.columns)

    def _header(self, title=None):
        self._set_align("center")
        self._set_size(2, 2)
        self._set_bold(True)
        self._line(self.store_name)
        self._set_size(1, 1)
        self._set_bold(False)
        if self.store_tagline:
            self._line(self.store_tagline)
        self._line(self.store_address)
        self._line(self.store_phone)
        self._set_align("left")
        self._rule("=")
        if title:
            self._set_align("center")
            self._set_bold(True)
            self._line(self._normalize_text(title).upper())
            self._set_bold(False)
            self._set_align("left")
            self._feed(1)

    def _footer(self, notes=None):
        self._line("=" * self.columns)
        if notes:
            self._set_align("center")
            for note in notes:
                if note == "":
                    self._feed(1)
                    continue
                for line in textwrap.wrap(self._normalize_text(note), width=self.columns):
                    self._line(line)
        else:
            self._set_align("center")
            self._line("")
            self._line("TERIMA KASIH ATAS KUNJUNGAN ANDA")
            self._line("Barang yang sudah dibeli tidak dapat")
            self._line("ditukar atau dikembalikan.")
            self._line("")
            self._line("www.adikarya.co")
            if self.footer_note:
                self._line(self.footer_note)
            self._line("")
        self._set_align("left")
        # Keep trailing feed at zero so the next receipt does not start with a large top blank.
        self._feed(0)
        # GS V A n: partial cut with feed n=3 (aligned with experiment view).
        self._buffer.extend(b"\x1dV\x41\x03")

    def _money(self, amount):
        value = Decimal("0") if amount in (None, "") else Decimal(str(amount))
        return f"Rp {int(value):,}".replace(",", ".")

    def _user_display(self, user):
        if not user:
            return "-"
        full_name = ""
        if hasattr(user, "get_full_name"):
            full_name = user.get_full_name() or ""
        username = getattr(user, "username", "") or str(user)
        return full_name or username

    def _kv(self, label, value):
        label_text = f"{self._normalize_text(label):<12}"
        value_text = self._normalize_text(value)
        available = max(12, self.columns - 15)
        lines = textwrap.wrap(value_text, width=available) or ["-"]
        self._line(f"{label_text} : {lines[0]}")
        for line in lines[1:]:
            self._line(f"{'':<12}   {line}")

    def _item_line(self, name, qty, unit_price, subtotal):
        item_name = self._normalize_text(name)
        for line in textwrap.wrap(item_name, width=self.columns):
            self._line(line)

        left = f"  {qty} x {self._money(unit_price)}"
        right = self._money(subtotal)
        gap = self.columns - len(left) - len(right)
        self._line(f"{left}{' ' * max(1, gap)}{right}")

    def _left_paragraph(self, lines):
        self._set_align("left")
        for line in lines:
            if line == "":
                self._feed(1)
                continue
            for chunk in textwrap.wrap(self._normalize_text(line), width=self.columns):
                self._line(chunk)

    def _total_row(self, label, value_text, bold=False):
        if bold:
            self._set_bold(True)
        gap = self.columns - len(label) - len(value_text) - 3  # ' : '
        self._line(f"{label}{' ' * max(1, gap)} : {value_text}")
        if bold:
            self._set_bold(False)

    def build_transaction_receipt(self, trx, items=None, title=None):
        if title is None:
            if trx.trx_type == "SALE":
                title = "STRUK PENJUALAN"
            elif trx.trx_type == "PURCHASE":
                title = "STRUK PEMBELIAN"
            else:
                title = "INVOICE TRANSAKSI"

        self._header(title)
        self._kv("No. Nota", trx.invoice_number)
        self._kv("Tanggal", localtime(
            trx.created_at).strftime("%d/%m/%Y %H:%M"))
        self._kv("Kasir", self._user_display(trx.created_by))
        if getattr(trx, "branch", None):
            self._kv("Cabang", trx.branch.name)
        if getattr(trx, "contact", None):
            self._kv("Pelanggan", trx.contact.name)

        self._feed(1)
        self._rule("-")
        for item in items or trx.items.select_related("product").all():
            subtotal = Decimal(str(item.qty)) * Decimal(str(item.price_at_trx))
            self._item_line(item.product.name, item.qty,
                            item.price_at_trx, subtotal)
        self._rule("-")

        self._total_row("TOTAL", self._money(trx.total_amount), bold=True)
        self._total_row("BAYAR", self._money(trx.amount_paid), bold=False)

        sisa = Decimal(str(trx.amount_paid or 0)) - \
            Decimal(str(trx.total_amount or 0))
        if sisa >= 0:
            self._total_row("KEMBALI", self._money(sisa), bold=True)
        else:
            self._total_row("KURANG", self._money(abs(sisa)), bold=True)

        self._feed(1)
        self._line(f"Metode Bayar: {trx.get_payment_method_display()}")
        if trx.due_date:
            self._line(f"Jatuh Tempo : {trx.due_date.strftime('%d/%m/%Y')}")

        self._footer()
        return self.output()

    def build_service_intake_receipt(self, service_ticket):
        self._header("TANDA TERIMA SERVIS")
        self._kv("No. Tiket", service_ticket.ticket_number)
        self._kv("Tanggal", localtime(
            service_ticket.created_at).strftime("%d/%m/%Y %H:%M"))
        self._kv("Petugas", self._user_display(service_ticket.created_by))
        self._kv("Cabang", service_ticket.branch.name)
        self._kv("Pelanggan", service_ticket.customer.name)
        self._kv("No. HP", getattr(
            service_ticket.customer, "whatsapp", "") or "-")

        self._feed(1)
        self._rule("-")
        self._line("DATA PERANGKAT")
        self._line(f"Barang   : {service_ticket.device_name}")
        if service_ticket.device_type:
            self._line(f"Jenis    : {service_ticket.device_type}")
        if service_ticket.device_brand:
            self._line(f"Merek    : {service_ticket.device_brand}")
        if service_ticket.serial_number:
            self._line(f"S/N      : {service_ticket.serial_number}")
        if service_ticket.device_color:
            self._line(f"Warna    : {service_ticket.device_color}")

        self._feed(1)
        self._line("KELENGKAPAN")
        self._line(", ".join(service_ticket.completeness)
                   if service_ticket.completeness else "-")
        if service_ticket.completeness_notes:
            self._line(f"Catatan : {service_ticket.completeness_notes}")

        self._feed(1)
        self._line("KELUHAN")
        for line in textwrap.wrap(self._normalize_text(service_ticket.complaint), width=self.columns):
            self._line(line)

        # warranty = getattr(service_ticket, "warranty_days", None) or 14
        # self._feed(1)
        # self._left_paragraph([
        #     "Syarat & Ketentuan Servis:",
        #     "1. Tanda terima ini harus dibawa saat pengambilan barang.",
        #     "2. Barang yang tidak diambil dalam 30 hari di luar tanggung jawab kami.",
        #     f"3. Garansi servis berlaku {warranty} hari.",
        # ])

        self._footer([
            "",
            "Mohon membawa tanda terima ini",
            "saat pengambilan. Barang yang tidak",
            "diambil dalam 30 hari setelah servis",
            "selesai di luar tanggung jawab kami.",
            f"Garansi servis berlaku {service_ticket.warranty_days or 14} hari.",
            "",
            "Hormat Kami,          Pelanggan,",
            "",
            "",
            "___________           ___________",
            "",
        ])
        return self.output()

    def build_service_invoice(self, service_ticket, header):
        self._header("INVOICE SERVIS")
        self._kv("No. Invoice", header.invoice_number)
        self._kv("No. Tiket", service_ticket.ticket_number)
        self._kv("Tanggal", localtime(header.created_at).strftime("%d/%m/%Y %H:%M")
                 if header else localtime(service_ticket.created_at).strftime("%d/%m/%Y %H:%M"))
        self._kv("Pelanggan", service_ticket.customer.name)
        self._kv("Cabang", service_ticket.branch.name)
        self._kv("Perangkat", service_ticket.device_name)
        if service_ticket.serial_number:
            self._kv("S/N", service_ticket.serial_number)

        self._feed(1)
        self._rule("-")
        subtotal = Decimal(str(getattr(header, "total_amount", 0) or 0))
        discount = Decimal(str(service_ticket.discount_amount or 0))
        grand_total = subtotal
        self._line("RINCIAN BIAYA")
        self._line(f"{'Biaya Servis':<18}{self._money(subtotal):>24}")
        if discount > 0:
            self._line(f"{'Diskon':<18}{('- ' + self._money(discount)):>24}")
        self._rule("-")
        self._line(f"{'TOTAL':<18}{self._money(grand_total):>24}")

        amount_paid = Decimal(str(getattr(header, "amount_paid", 0) or 0))
        self._line(f"{'Dibayar':<18}{self._money(amount_paid):>24}")
        remaining = grand_total - amount_paid
        if remaining > 0:
            self._line(f"{'Sisa Piutang':<18}{self._money(remaining):>24}")
        elif remaining < 0:
            self._line(f"{'Kembalian':<18}{self._money(abs(remaining)):>24}")

        self._feed(1)
        self._line(
            f"Metode Bayar: {getattr(header, 'get_payment_method_display', lambda: 'Tunai')()}")
        if getattr(header, "due_date", None):
            self._line(f"Jatuh Tempo : {header.due_date.strftime('%d/%m/%Y')}")
        if service_ticket.invoice_notes:
            self._feed(1)
            self._line("CATATAN INVOICE")
            for line in textwrap.wrap(self._normalize_text(service_ticket.invoice_notes), width=self.columns):
                self._line(line)
        if service_ticket.warranty_days:
            self._feed(1)
            self._line(f"Garansi servis: {service_ticket.warranty_days} hari")

        self._footer([
            "Terima kasih atas kepercayaan Anda.",
            "Simpan invoice ini untuk klaim garansi servis.",
        ])
        return self.output()
