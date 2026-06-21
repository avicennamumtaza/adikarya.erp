from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.service.models import ServiceTicket
from apps.partner.models import Contact
from apps.inventory.models import Branch


class Command(BaseCommand):
    help = 'Seed initial service tickets data'

    def handle(self, *args, **options):
        # Ensure we have at least one Contact and Branch
        contact, _ = Contact.objects.get_or_create(
            name="John Doe",
            defaults={"whatsapp": "081234567890", "email": "john@example.com", "contact_type": "CUSTOMER"}
        )

        branch, _ = Branch.objects.get_or_create(
            name="Pusat",
            defaults={"address": "Jl. Utama No. 1"}
        )

        tickets_data = [
            {
                "ticket_number": "TKT-001",
                "customer": contact,
                "branch": branch,
                "checkin_date": timezone.now().date(),
                "device_type": "Laptop",
                "device_brand": "Lenovo",
                "device_name": "Lenovo ThinkPad T14",
                "serial_number": "SN12345678",
                "device_color": "Black",
                "completeness": ["Charger", "Tas"],
                "condition": ["Goresan tipis di cover"],
                "complaint": "Mati total, tidak bisa nyala.",
                "status": "DIAGNOSING",
            },
            {
                "ticket_number": "TKT-002",
                "customer": contact,
                "branch": branch,
                "checkin_date": timezone.now().date(),
                "device_type": "Smartphone",
                "device_brand": "Samsung",
                "device_name": "Samsung Galaxy S21",
                "serial_number": "SMG991B",
                "device_color": "Phantom Gray",
                "completeness": ["Unit Only"],
                "condition": ["Layar retak"],
                "complaint": "Layar pecah setelah jatuh.",
                "status": "WAITING",
            }
        ]

        created_count = 0
        updated_count = 0

        for data in tickets_data:
            ticket, created = ServiceTicket.objects.update_or_create(
                ticket_number=data['ticket_number'],
                defaults=data
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Successfully created service ticket: {ticket.ticket_number}"))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f"Successfully updated service ticket: {ticket.ticket_number}"))

        self.stdout.write(self.style.SUCCESS(f"\nSummary: {created_count} tickets created, {updated_count} tickets updated."))
