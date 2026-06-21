"""Seed ServiceTicket data for a computer repair shop."""
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.inventory.models import Branch
from apps.partner.models import Contact
from apps.service.models import ServiceTicket


TICKETS = [
    {
        'customer_name': 'Rina Wulandari',
        'device_type': 'Laptop', 'device_brand': 'ASUS',
        'device_name': 'ASUS VivoBook 14 X1404VA',
        'serial_number': 'L8N0CV03K912345',
        'device_color': 'Silver',
        'completeness': ['Charger', 'Tas'],
        'condition': ['Layar normal', 'Body lecet ringan'],
        'complaint': 'Laptop mati total, tidak bisa dinyalakan setelah jatuh dari meja.',
        'status': 'REPAIRING',
        'warranty_days': 30,
        'days_ago': 3,
    },
    {
        'customer_name': 'Hadi Prasetyo',
        'device_type': 'PC Desktop', 'device_brand': 'Rakitan',
        'device_name': 'PC Rakitan Intel i5-12400',
        'serial_number': '',
        'device_color': 'Hitam',
        'completeness': ['Kabel Power'],
        'condition': ['Casing normal', 'Berdebu'],
        'complaint': 'PC sering restart sendiri saat main game. Diduga masalah PSU atau overheat.',
        'status': 'DIAGNOSING',
        'warranty_days': 14,
        'days_ago': 1,
    },
    {
        'customer_name': 'CV Maju Jaya',
        'device_type': 'Printer', 'device_brand': 'Epson',
        'device_name': 'Epson L3250',
        'serial_number': 'X5LK-2301-7890',
        'device_color': 'Hitam',
        'completeness': ['Kabel USB', 'Kabel Power'],
        'condition': ['Body normal', 'Nozzle tersumbat'],
        'complaint': 'Hasil print bergaris dan warna tidak keluar merata. Sudah coba head cleaning tapi tetap.',
        'status': 'DONE',
        'warranty_days': 7,
        'days_ago': 7,
    },
    {
        'customer_name': 'Warnet GG Gaming',
        'device_type': 'PC Desktop', 'device_brand': 'Rakitan',
        'device_name': 'PC Client Warnet #3',
        'serial_number': '',
        'device_color': 'Hitam',
        'completeness': ['Kabel Power'],
        'condition': ['Casing penyok ringan'],
        'complaint': 'Blue screen WHEA_UNCORRECTABLE_ERROR terus menerus. Diduga masalah RAM atau SSD.',
        'status': 'WAITING',
        'warranty_days': 14,
        'days_ago': 5,
        'invoice_notes': 'Part SSD pengganti sedang dipesan dari supplier.',
    },
    {
        'customer_name': 'Rina Wulandari',
        'device_type': 'Laptop', 'device_brand': 'Lenovo',
        'device_name': 'Lenovo IdeaPad Slim 3',
        'serial_number': 'PF3N1234W',
        'device_color': 'Biru',
        'completeness': ['Charger'],
        'condition': ['Layar retak pojok kanan bawah'],
        'complaint': 'LCD retak, minta ganti LCD baru.',
        'status': 'PICKED',
        'warranty_days': 30,
        'days_ago': 14,
    },
    {
        'customer_name': 'Hadi Prasetyo',
        'device_type': 'Laptop', 'device_brand': 'HP',
        'device_name': 'HP 245 G10',
        'serial_number': 'CND4231RKT',
        'device_color': 'Dark Silver',
        'completeness': ['Charger', 'Dos'],
        'condition': ['Body normal', 'Keyboard normal'],
        'complaint': 'Laptop sangat lambat, minta upgrade RAM dan ganti SSD.',
        'status': 'RECEIVED',
        'warranty_days': 14,
        'days_ago': 0,
    },
]


class Command(BaseCommand):
    help = 'Seed service ticket data'

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true')

    def handle(self, *args, **options):
        if options['flush']:
            ServiceTicket.objects.all().delete()
            self.stdout.write(self.style.WARNING('  Flushed service tickets'))

        branch = Branch.objects.first()
        if not branch:
            self.stdout.write(self.style.ERROR('  No branch found.'))
            return

        contacts_by_name = {c.name: c for c in Contact.objects.all()}
        now = timezone.now()
        seq = ServiceTicket.objects.count() + 1

        for data in TICKETS:
            contact = contacts_by_name.get(data['customer_name'])
            if not contact:
                self.stdout.write(self.style.WARNING(
                    f'  [SKIP] Customer not found: {data["customer_name"]}'))
                continue

            ticket_number = f'SVC-{now.strftime("%Y%m")}-{seq:04d}'
            seq += 1

            if ServiceTicket.objects.filter(ticket_number=ticket_number).exists():
                self.stdout.write(f'  [SKIP] {ticket_number} exists')
                continue

            checkin = (now - timedelta(days=data.get('days_ago', 0))).date()

            ServiceTicket.objects.create(
                ticket_number=ticket_number,
                customer=contact,
                branch=branch,
                checkin_date=checkin,
                device_type=data.get('device_type', ''),
                device_brand=data.get('device_brand', ''),
                device_name=data['device_name'],
                serial_number=data.get('serial_number', ''),
                device_color=data.get('device_color', ''),
                completeness=data.get('completeness', []),
                condition=data.get('condition', []),
                complaint=data['complaint'],
                invoice_notes=data.get('invoice_notes', ''),
                warranty_days=data.get('warranty_days', 0),
                customer_agreement=True,
                status=data['status'],
            )
            self.stdout.write(
                f'  [CREATED] {ticket_number} — {data["device_name"]} '
                f'({data["status"]})')

        self.stdout.write(self.style.SUCCESS(
            f'  Done — {ServiceTicket.objects.count()} tickets total'))
