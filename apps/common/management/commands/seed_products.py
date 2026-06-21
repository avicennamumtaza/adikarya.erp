"""Seed Product & Stock data for a computer store."""
from decimal import Decimal
from django.core.management.base import BaseCommand
from apps.inventory.models import Product, Stock, Branch

PRODUCTS = [
    # ── Laptop ──
    {'sku': 'LPT-001', 'name': 'Laptop ASUS VivoBook 14 X1404VA', 'category': 'Laptop',
     'brand': 'ASUS', 'base_price': 6800000, 'selling_price': 7499000, 'min_stock': 3,
     'docs': 'https://www.asus.com/id/laptops/for-home/vivobook/vivobook-14-x1404/'},
    {'sku': 'LPT-002', 'name': 'Laptop Lenovo IdeaPad Slim 3 14IAH8', 'category': 'Laptop',
     'brand': 'Lenovo', 'base_price': 7200000, 'selling_price': 7999000, 'min_stock': 3},
    {'sku': 'LPT-003', 'name': 'Laptop HP 245 G10 Ryzen 5', 'category': 'Laptop',
     'brand': 'HP', 'base_price': 6500000, 'selling_price': 7250000, 'min_stock': 2},
    {'sku': 'LPT-004', 'name': 'Laptop Acer Aspire 5 A515-58M', 'category': 'Laptop',
     'brand': 'Acer', 'base_price': 8500000, 'selling_price': 9399000, 'min_stock': 2},
    # ── Desktop / PC Rakitan ──
    {'sku': 'PC-001', 'name': 'PC Rakitan Intel i3-12100 / 8GB / SSD 256GB',
     'category': 'PC Desktop', 'brand': 'Rakitan',
     'base_price': 4200000, 'selling_price': 4850000, 'min_stock': 3},
    {'sku': 'PC-002', 'name': 'PC Rakitan Intel i5-12400 / 16GB / SSD 512GB',
     'category': 'PC Desktop', 'brand': 'Rakitan',
     'base_price': 6100000, 'selling_price': 6999000, 'min_stock': 2},
    {'sku': 'PC-003', 'name': 'PC Rakitan AMD Ryzen 5 5600G / 16GB / SSD 512GB',
     'category': 'PC Desktop', 'brand': 'Rakitan',
     'base_price': 5800000, 'selling_price': 6650000, 'min_stock': 2},
    # ── Printer ──
    {'sku': 'PRN-001', 'name': 'Printer Epson L3250 EcoTank', 'category': 'Printer',
     'brand': 'Epson', 'base_price': 3100000, 'selling_price': 3450000, 'min_stock': 3},
    {'sku': 'PRN-002', 'name': 'Printer HP Smart Tank 515', 'category': 'Printer',
     'brand': 'HP', 'base_price': 2800000, 'selling_price': 3150000, 'min_stock': 2},
    {'sku': 'PRN-003', 'name': 'Printer Canon PIXMA G3020', 'category': 'Printer',
     'brand': 'Canon', 'base_price': 2700000, 'selling_price': 3050000, 'min_stock': 2},
    {'sku': 'PRN-004', 'name': 'Printer Brother DCP-T426W', 'category': 'Printer',
     'brand': 'Brother', 'base_price': 2500000, 'selling_price': 2850000, 'min_stock': 2},
    # ── Monitor ──
    {'sku': 'MON-001', 'name': 'Monitor LG 22MK430H 22" IPS', 'category': 'Monitor',
     'brand': 'LG', 'base_price': 1550000, 'selling_price': 1799000, 'min_stock': 3},
    {'sku': 'MON-002', 'name': 'Monitor Samsung LS24C360 24" FHD', 'category': 'Monitor',
     'brand': 'Samsung', 'base_price': 1800000, 'selling_price': 2099000, 'min_stock': 2},
    # ── Komponen ──
    {'sku': 'KMP-001', 'name': 'RAM DDR4 8GB 3200MHz Corsair Vengeance', 'category': 'Komponen',
     'brand': 'Corsair', 'base_price': 280000, 'selling_price': 359000, 'min_stock': 10},
    {'sku': 'KMP-002', 'name': 'SSD NVMe 512GB Samsung 980', 'category': 'Komponen',
     'brand': 'Samsung', 'base_price': 650000, 'selling_price': 789000, 'min_stock': 5},
    {'sku': 'KMP-003', 'name': 'SSD SATA 240GB Kingston A400', 'category': 'Komponen',
     'brand': 'Kingston', 'base_price': 280000, 'selling_price': 339000, 'min_stock': 8},
    {'sku': 'KMP-004', 'name': 'PSU Corsair CV450 450W 80+ Bronze', 'category': 'Komponen',
     'brand': 'Corsair', 'base_price': 520000, 'selling_price': 629000, 'min_stock': 4},
    {'sku': 'KMP-005', 'name': 'Casing PC NZXT H5 Flow ATX', 'category': 'Komponen',
     'brand': 'NZXT', 'base_price': 850000, 'selling_price': 999000, 'min_stock': 3},
    # ── Aksesoris ──
    {'sku': 'AKS-001', 'name': 'Keyboard Logitech K120 USB', 'category': 'Aksesoris',
     'brand': 'Logitech', 'base_price': 95000, 'selling_price': 125000, 'min_stock': 10},
    {'sku': 'AKS-002', 'name': 'Mouse Logitech B100 USB', 'category': 'Aksesoris',
     'brand': 'Logitech', 'base_price': 55000, 'selling_price': 75000, 'min_stock': 15},
    {'sku': 'AKS-003', 'name': 'Keyboard Mouse Combo Logitech MK270R', 'category': 'Aksesoris',
     'brand': 'Logitech', 'base_price': 250000, 'selling_price': 315000, 'min_stock': 5},
    {'sku': 'AKS-004', 'name': 'Headset Rexus Vonix HX20', 'category': 'Aksesoris',
     'brand': 'Rexus', 'base_price': 120000, 'selling_price': 165000, 'min_stock': 5},
    {'sku': 'AKS-005', 'name': 'Kabel HDMI 1.5m Gold Plated', 'category': 'Aksesoris',
     'brand': 'Generic', 'base_price': 25000, 'selling_price': 45000, 'min_stock': 20},
    {'sku': 'AKS-006', 'name': 'Tas Laptop 14" Navy Club', 'category': 'Aksesoris',
     'brand': 'Navy Club', 'base_price': 85000, 'selling_price': 135000, 'min_stock': 5},
    {'sku': 'AKS-007', 'name': 'Flashdisk Sandisk 32GB CZ73', 'category': 'Aksesoris',
     'brand': 'Sandisk', 'base_price': 55000, 'selling_price': 79000, 'min_stock': 15},
    {'sku': 'AKS-008', 'name': 'Tinta Epson 003 Black Original', 'category': 'Aksesoris',
     'brand': 'Epson', 'base_price': 72000, 'selling_price': 95000, 'min_stock': 10},
    {'sku': 'AKS-009', 'name': 'Tinta Epson 003 Cyan/Magenta/Yellow', 'category': 'Aksesoris',
     'brand': 'Epson', 'base_price': 72000, 'selling_price': 95000, 'min_stock': 8},
    # ── Networking ──
    {'sku': 'NET-001', 'name': 'Router TP-Link Archer C6 AC1200', 'category': 'Networking',
     'brand': 'TP-Link', 'base_price': 380000, 'selling_price': 459000, 'min_stock': 4},
    {'sku': 'NET-002', 'name': 'Switch TP-Link TL-SG108 8-Port Gigabit', 'category': 'Networking',
     'brand': 'TP-Link', 'base_price': 250000, 'selling_price': 315000, 'min_stock': 3},
    {'sku': 'NET-003', 'name': 'Kabel UTP Cat6 Belden 1 Roll (305m)', 'category': 'Networking',
     'brand': 'Belden', 'base_price': 1500000, 'selling_price': 1750000, 'min_stock': 2},
    # ── Jasa / Service ──
    {'sku': 'SRV-001', 'name': 'Jasa Install Ulang Windows + Driver',
     'category': 'Jasa', 'brand': '', 'product_type': 'SERVICE',
     'base_price': 0, 'selling_price': 100000, 'min_stock': 0},
    {'sku': 'SRV-002', 'name': 'Jasa Service Ringan (Cleaning + Checkup)',
     'category': 'Jasa', 'brand': '', 'product_type': 'SERVICE',
     'base_price': 0, 'selling_price': 75000, 'min_stock': 0},
    {'sku': 'SRV-003', 'name': 'Jasa Service Berat (Ganti Komponen)',
     'category': 'Jasa', 'brand': '', 'product_type': 'SERVICE',
     'base_price': 0, 'selling_price': 150000, 'min_stock': 0},
    {'sku': 'SRV-004', 'name': 'Jasa Rakit PC Custom',
     'category': 'Jasa', 'brand': '', 'product_type': 'SERVICE',
     'base_price': 0, 'selling_price': 200000, 'min_stock': 0},
    {'sku': 'SRV-005', 'name': 'Jasa Ganti LCD Laptop',
     'category': 'Jasa', 'brand': '', 'product_type': 'SERVICE',
     'base_price': 0, 'selling_price': 125000, 'min_stock': 0},
    {'sku': 'SRV-006', 'name': 'Jasa Recovery Data',
     'category': 'Jasa', 'brand': '', 'product_type': 'SERVICE',
     'base_price': 0, 'selling_price': 200000, 'min_stock': 0},
    {'sku': 'SRV-007', 'name': 'Jasa Pasang CCTV (per titik)',
     'category': 'Jasa', 'brand': '', 'product_type': 'SERVICE',
     'base_price': 0, 'selling_price': 150000, 'min_stock': 0},
]

# Stock quantities per branch index: {sku: [pusat_qty, cabang_qty]}
STOCK_MAP = {
    'LPT-001': [5, 3], 'LPT-002': [4, 2], 'LPT-003': [3, 1], 'LPT-004': [2, 1],
    'PC-001': [4, 2], 'PC-002': [3, 1], 'PC-003': [3, 1],
    'PRN-001': [6, 3], 'PRN-002': [4, 2], 'PRN-003': [3, 2], 'PRN-004': [3, 1],
    'MON-001': [5, 3], 'MON-002': [3, 2],
    'KMP-001': [20, 8], 'KMP-002': [10, 5], 'KMP-003': [15, 6],
    'KMP-004': [6, 3], 'KMP-005': [4, 2],
    'AKS-001': [20, 10], 'AKS-002': [25, 12], 'AKS-003': [8, 4],
    'AKS-004': [6, 3], 'AKS-005': [30, 15], 'AKS-006': [8, 3],
    'AKS-007': [20, 10], 'AKS-008': [15, 8], 'AKS-009': [12, 6],
    'NET-001': [5, 3], 'NET-002': [4, 2], 'NET-003': [3, 1],
}


class Command(BaseCommand):
    help = 'Seed product & stock data'

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true')

    def handle(self, *args, **options):
        if options['flush']:
            Stock.objects.all().delete()
            Product.objects.all().delete()
            self.stdout.write(self.style.WARNING('  Flushed products & stock'))

        branches = list(Branch.objects.order_by('id'))
        if not branches:
            self.stdout.write(self.style.ERROR('  No branches found. Run seed_branches first.'))
            return

        for data in PRODUCTS:
            defaults = {
                'name': data['name'],
                'product_type': data.get('product_type', 'PRODUCT'),
                'category': data.get('category', ''),
                'brand': data.get('brand', ''),
                'base_price': Decimal(str(data['base_price'])),
                'selling_price': Decimal(str(data['selling_price'])),
                'min_stock': data.get('min_stock', 2),
                'notes': data.get('notes', ''),
                'docs': data.get('docs', ''),
            }
            product, created = Product.objects.update_or_create(
                sku=data['sku'], defaults=defaults)
            tag = 'CREATED' if created else 'UPDATED'
            self.stdout.write(f'  [{tag}] {product.sku} — {product.name}')

            # Assign stock
            qtys = STOCK_MAP.get(data['sku'])
            if qtys:
                for i, qty in enumerate(qtys):
                    if i < len(branches):
                        Stock.objects.update_or_create(
                            product=product, branch=branches[i],
                            defaults={'quantity': qty})

        self.stdout.write(self.style.SUCCESS(
            f'  Done — {Product.objects.count()} products, '
            f'{Stock.objects.count()} stock records'))
