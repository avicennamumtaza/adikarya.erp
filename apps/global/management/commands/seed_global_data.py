from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings

# Use importlib to avoid mysterious SyntaxError with 'from apps...' on Python 3.12
import importlib
gm = importlib.import_module('apps.global.models')
im = importlib.import_module('apps.inventory.models')

CompanyProfile = gm.CompanyProfile
CompanyStat = gm.CompanyStat
CompanyValue = gm.CompanyValue
TickerText = gm.TickerText
TeamMember = gm.TeamMember
PartnerBrand = gm.PartnerBrand
Testimonial = gm.Testimonial
Promo = gm.Promo
FAQ = gm.FAQ
GalleryCategory = gm.GalleryCategory
Gallery = gm.Gallery
ArticleCategory = gm.ArticleCategory
Article = gm.Article
Branch = im.Branch


class Command(BaseCommand):
    help = "Seed database with initial data for Zona Komputer Bojonegoro"

    def handle(self, *args, **options):
        self._seed_company()
        self._seed_stats()
        self._seed_values()
        self._seed_tickers()
        self._seed_team()
        self._seed_brands()
        self._seed_faqs()
        self._seed_testimonials()
        self._seed_promos()
        self._seed_gallery()
        self._seed_articles()
        self._seed_branches()
        self.stdout.write(self.style.SUCCESS('All data seeded successfully!'))

    def _seed_company(self):
        if CompanyProfile.objects.exists():
            self.stdout.write('  CompanyProfile already exists, skipping.')
            return
        CompanyProfile.objects.create(
            name='Zona Komputer',
            short_description='Toko komputer, laptop & printer di Bojonegoro. Melayani penjualan, servis, dan upgrade — jujur, bergaransi, dipercaya lebih dari 25 tahun.',
            about_text='<p>Berdiri sejak 1999, <strong>Zona Komputer</strong> dimulai dari toko kecil di Jl. Veteran Bojonegoro. Bermodalkan keahlian servis dan kejujuran, kami perlahan dipercaya oleh masyarakat Bojonegoro untuk menangani berbagai kebutuhan komputer — dari sekadar beli mouse hingga servis laptop mati total.</p><p>Satu prinsip yang tidak pernah berubah: <strong>kondisi perangkat disampaikan apa adanya, estimasi biaya sebelum dikerjakan, garansi tertulis untuk setiap servis.</strong> Itu sebabnya pelanggan kami — dari pelajar, mahasiswa, guru, hingga kantor-kantor di Bojonegoro — tetap setia sampai sekarang.</p><p>Saat ini, Zona Komputer terus berkembang. Stok kami semakin lengkap, teknisi kami terus belajar teknologi baru, dan toko kami tetap menjadi tempat yang ramah untuk sekadar bertanya seputar komputer.</p>',
            address='Jl. Veteran No. 10, Bojonegoro',
            phone='0821-4060-3875',
            whatsapp='6282140603875',
            email='zonakomputer.bojonegoro@gmail.com',
            operational_hours='Senin – Sabtu, 08.00 – 17.00',
            maps_url='https://maps.google.com/?q=-7.15382,111.88618',
            instagram_url='https://instagram.com/zonakomputer.bjn',
            facebook_url='https://facebook.com/zonakomputer.bjn',
            tiktok_url='',
            visi='Menjadi mitra teknologi nomor satu bagi masyarakat Bojonegoro dan sekitarnya — dari generasi ke generasi.',
            misi='Produk & servis berkualitas, harga transparan. Teknisi kompeten yang terus belajar. Hubungan jangka panjang berbasis kepercayaan.',
        )
        self.stdout.write('  CompanyProfile created.')

    def _seed_stats(self):
        if CompanyStat.objects.exists():
            self.stdout.write('  CompanyStat already exists, skipping.')
            return
        stats = [
            ('Tahun Berdiri', '1999', 'Melayani Bojonegoro sejak 1999', '🏆', 1),
            ('Pengalaman', '25+', 'Tahun pengalaman jual & servis', '📅', 2),
            ('Pelanggan', '5000+', 'Pelanggan setia dari berbagai kalangan', '👥', 3),
            ('Unit Ditangani', '10000+', 'Ribuan unit laptop, PC & printer', '🔧', 4),
            ('Garansi Servis', '30 Hari', 'Garansi tertulis untuk tiap pekerjaan', '🛡️', 5),
        ]
        for title, value, desc, icon, order in stats:
            CompanyStat.objects.create(title=title, value=value, description=desc, icon=icon, order=order)
        self.stdout.write('  %d CompanyStats created.' % len(stats))

    def _seed_values(self):
        if CompanyValue.objects.exists():
            self.stdout.write('  CompanyValue already exists, skipping.')
            return
        values = [
            ('JUJUR', 'Kondisi perangkat disampaikan apa adanya, tanpa ditutup-tutupi.', '🤝', 1),
            ('TRANSPARAN', 'Estimasi biaya sebelum dikerjakan. Tidak ada biaya kejutan.', '📋', 2),
            ('BERGARANSI', 'Setiap servis dilengkapi kartu garansi tertulis 30 hari.', '🛡️', 3),
            ('KOMPETEN', 'Teknisi terus belajar dan mengikuti perkembangan teknologi terbaru.', '📚', 4),
            ('RAMAH', 'Toko yang terbuka untuk diskusi dan konsultasi — bukan sekadar transaksi.', '😊', 5),
        ]
        for title, desc, icon, order in values:
            CompanyValue.objects.create(title=title, description=desc, icon=icon, order=order)
        self.stdout.write('  %d CompanyValues created.' % len(values))

    def _seed_tickers(self):
        if TickerText.objects.exists():
            self.stdout.write('  TickerText already exists, skipping.')
            return
        tickers = [
            'Garansi Servis 30 Hari — Tertulis, Bukan Janji',
            'Diagnosa Gratis — Biaya Diketahui Sebelum Servis Dimulai',
            'Sparepart Original Bergaransi',
            'Melayani Servis Laptop, PC, Printer & Jaringan',
            'Booking Servis Online — Datang Langsung Dikerjakan',
            'Upgrade SSD & RAM — Laptop Ngebut Kembali',
            'Konsultasi Gratis Sebelum Beli atau Servis',
            'Jual Laptop Baru & Second Berkualitas',
            'Rakit PC Sesuai Budget & Kebutuhan',
            'Jangan Dibuang Dulu — Mungkin Masih Bisa Diservis',
        ]
        for i, text in enumerate(tickers, 1):
            TickerText.objects.create(text=text, is_active=True, order=i)
        self.stdout.write('  %d TickerTexts created.' % len(tickers))

    def _seed_team(self):
        if TeamMember.objects.exists():
            self.stdout.write('  TeamMember already exists, skipping.')
            return
        members = [
            ('Hadi', 'Pemilik & Founder', 'Servis Hardware, Manajemen Toko', '25+ tahun', 1),
            ('Arif', 'Teknisi Senior', 'Servis Laptop, PC, Printer', '15+ tahun', 2),
            ('Dimas', 'Teknisi', 'Servis Software, Jaringan, Upgrade', '8 tahun', 3),
            ('Sari', 'Admin & Customer Service', 'Pelayanan pelanggan, stok & penjualan', '5 tahun', 4),
        ]
        for name, role, specialty, exp, order in members:
            TeamMember.objects.create(name=name, role=role, specialty=specialty, experience=exp, order=order)
        self.stdout.write('  %d TeamMembers created.' % len(members))

    def _seed_brands(self):
        if PartnerBrand.objects.exists():
            self.stdout.write('  PartnerBrand already exists, skipping.')
            return
        brands = [
            ('ASUS', 1), ('ACER', 2), ('Lenovo', 3), ('HP', 4),
            ('DELL', 5), ('Apple', 6), ('Samsung', 7), ('Toshiba', 8),
            ('Epson', 9), ('Canon', 10), ('Brother', 11), ('TP-Link', 12),
            ('D-Link', 13), ('Logitech', 14), ('Kingston', 15), ('WD', 16),
            ('Seagate', 17), ('Corsair', 18), ('V-GeN', 19), ('Rexus', 20),
        ]
        for name, order in brands:
            PartnerBrand.objects.create(name=name, is_active=True, order=order)
        self.stdout.write('  %d PartnerBrands created.' % len(brands))

    def _seed_faqs(self):
        if FAQ.objects.exists():
            self.stdout.write('  FAQ already exists, skipping.')
            return
        faqs = [
            ('Berapa biaya servis laptop?', 'Biaya servis bervariasi tergantung kerusakan. Kami selalu melakukan diagnosa terlebih dahulu dan memberikan estimasi biaya sebelum melakukan perbaikan. Biaya diagnosa gratis jika perbaikan dilanjutkan.', 1),
            ('Apakah ada garansi untuk servis?', 'Ya, setiap pekerjaan servis dilengkapi dengan kartu garansi tertulis selama 30 hari. Jika keluhan yang sama muncul kembali dalam masa garansi, kami perbaiki tanpa biaya tambahan.', 2),
            ('Berapa lama waktu servis laptop?', 'Tergantung jenis kerusakan. Servis software seperti install ulang biasanya 1-2 jam. Servis hardware seperti ganti LCD bisa 1-2 hari. Kami akan informasikan estimasi waktu saat diagnosa.', 3),
            ('Apakah bisa konsultasi dulu sebelum servis?', 'Tentu! Anda bisa chat via WhatsApp atau datang langsung ke toko untuk konsultasi gratis. Kami akan menjelaskan kerusakan, biaya, dan waktu pengerjaan sebelum memutuskan.', 4),
            ('Apakah menjual laptop second?', 'Ya, kami menjual laptop second / recondition dengan kualitas terjamin. Setiap unit diperiksa, dibersihkan, dan di-test sebelum dijual. Garansi toko 30 hari untuk setiap pembelian.', 5),
            ('Bisa booking servis online?', 'Bisa! Silakan isi form booking di halaman Layanan & Servis, atau langsung chat via WhatsApp. Kami akan konfirmasi jadwal kedatangan Anda.', 6),
            ('Apakah ada layanan antar-jemput?', 'Ya, untuk area Bojonegoro kota kami menyediakan layanan antar-jemput perangkat. Silakan hubungi kami untuk koordinasi lebih lanjut.', 7),
            ('Metode pembayaran apa saja?', 'Kami menerima pembayaran Tunai, Transfer Bank (BCA, Mandiri, BRI), dan E-Wallet (GoPay, OVO, DANA, ShopeePay).', 8),
        ]
        for q, a, order in faqs:
            FAQ.objects.create(question=q, answer=a, is_active=True, order=order)
        self.stdout.write('  %d FAQs created.' % len(faqs))

    def _seed_testimonials(self):
        if Testimonial.objects.exists():
            self.stdout.write('  Testimonial already exists, skipping.')
            return
        testimonials = [
            ('Budi Santoso', 'Guru SMK', 'Laptop saya mati total dan data skripsi hampir hilang. Alhamdulillah data bisa diselamatkan dan laptop normal lagi. Makasih Zona Komputer!', 5, False, 1),
            ('Siti Nur Aini', 'Mahasiswa', 'Pertama kali ke sini buat beli laptop, dijelasin sabar banget. Akhirnya dapet unit yang sesuai budget. Recomended!', 5, False, 2),
            ('Pak RT.031', 'Wiraswasta', 'Sudah langganan servis printer di sini selama 5 tahun. Jujur, harganya wajar, dan selalu ready sparepart-nya.', 5, True, 3),
            ('Dinas Pendidikan', 'Instansi Pemerintah', 'Kerja sama pengadaan PC kantor. Pengiriman tepat waktu, barang sesuai spek, garansi toko. Profesional.', 5, True, 4),
            ('Rudi Hartono', 'Teknisi IT', 'Tempat langganan beli sparepart dan komponen. Stok lumayan lengkap, harga bersaing. Recomended untuk teman-teman IT Bojonegoro.', 5, False, 5),
            ('Yanti', 'Ibu Rumah Tangga', 'Anak saya butuh laptop buat sekolah online. Dapat unit second yang bagus, masih mulus, dan ada garansi. Terima kasih.', 4, False, 6),
            ('SMAN 1 Bojonegoro', 'Sekolah', 'Servis 20 unit PC laboratorium sekolah. Semua selesai tepat waktu dan sesuai budget. Terima kasih Zona Komputer.', 5, True, 7),
            ('Andi Prasetyo', 'Freelance Designer', 'Upgrade RAM dan SSD di sini. Hasilnya laptop jadi ngebut banget buat desain. Teknisinya paham banget.', 5, True, 8),
        ]
        for name, role, content, rating, featured, order in testimonials:
            Testimonial.objects.create(
                customer_name=name, customer_role=role, content=content,
                rating=rating, is_featured=featured, order=order,
                avatar_initial=name[0]
            )
        self.stdout.write('  %d Testimonials created.' % len(testimonials))

    def _seed_promos(self):
        if Promo.objects.exists():
            self.stdout.write('  Promo already exists, skipping.')
            return
        promos = [
            {
                'title': 'Pasang SSD Gratis Jasa',
                'category': 'Upgrade',
                'description': 'Beli SSD di tempat kami, jasa pasang + kloning data GRATIS. Promo berlaku untuk semua merek SSD yang tersedia.',
                'benefits': 'Gratis jasa pasang\nGratis kloning data\nSSD bergaransi resmi',
                'discount_text': 'Gratis Jasa',
                'call_to_action': 'Chat Sekarang',
                'wa_text': 'Halo, saya tertarik dengan promo Pasang SSD Gratis Jasa',
                'order': 1,
            },
            {
                'title': 'Paket Bundling Laptop + Aksesoris',
                'category': 'Produk',
                'description': 'Beli laptop baru di Zona Komputer, dapatkan paket bundling hemat: tas laptop + mouse wireless + keyboard combo.',
                'benefits': 'Diskon hingga Rp 150rb\nTas laptop eksklusif\nMouse + keyboard wireless',
                'discount_text': 'Hemat 150rb',
                'call_to_action': 'Lihat Paket',
                'wa_text': 'Halo, saya mau lihat paket bundling laptop',
                'order': 2,
            },
            {
                'title': 'Diskon Servis Akhir Tahun',
                'category': 'Servis',
                'description': 'Servis laptop, PC, atau printer dapat diskon 10% untuk semua jenis perbaikan. Cocok buat bersihin laptop sebelum tahun baru!',
                'benefits': 'Diskon 10% semua servis\nBersih + ganti thermal paste gratis\nKonsultasi gratis',
                'discount_text': 'Diskon 10%',
                'call_to_action': 'Booking Servis',
                'wa_text': 'Halo, saya mau booking servis promo akhir tahun',
                'order': 3,
            },
        ]
        for p in promos:
            Promo.objects.create(
                title=p['title'], category=p['category'],
                description=p['description'], benefits=p['benefits'],
                discount_text=p['discount_text'], call_to_action=p['call_to_action'],
                wa_text=p['wa_text'], is_active=True, order=p['order'],
            )
        self.stdout.write('  %d Promos created.' % len(promos))

    def _seed_gallery(self):
        if GalleryCategory.objects.exists():
            self.stdout.write('  Gallery already exists, skipping.')
            return
        cats = [
            ('Toko & Suasana', 1),
            ('Servis & Perbaikan', 2),
            ('Produk & Barang', 3),
            ('Tim Kami', 4),
            ('Kegiatan & Event', 5),
        ]
        for name, order in cats:
            GalleryCategory.objects.create(name=name, order=order)
        self.stdout.write('  %d GalleryCategories created.' % len(cats))

        items = [
            ('Tampak Depan Toko', 'Toko Zona Komputer di Jl. Veteran No. 10 Bojonegoro', '🏪', 'Toko & Suasana', 1),
            ('Ruang Servis', 'Area kerja teknisi dengan peralatan lengkap', '🔧', 'Servis & Perbaikan', 2),
            ('Rak Produk Laptop', 'Display laptop baru dan second siap jual', '💻', 'Produk & Barang', 3),
            ('Tim Zona Komputer', 'Foto bersama tim teknisi dan admin', '👥', 'Tim Kami', 4),
            ('Suasana Toko Pagi Hari', 'Toko siap melayani pelanggan', '☀️', 'Toko & Suasana', 5),
            ('Proses Servis Laptop', 'Teknisi sedang memperbaiki motherboard laptop', '⚡', 'Servis & Perbaikan', 6),
            ('Rak Sparepart & Komponen', 'Koleksi sparepart dan komponen siap pakai', '⚙️', 'Produk & Barang', 7),
            ('Sertifikat & Penghargaan', 'Dokumentasi sertifikat workshop teknisi', '📜', 'Tim Kami', 8),
        ]
        for title, desc, icon, cat_name, order in items:
            cat = GalleryCategory.objects.get(name=cat_name)
            Gallery.objects.create(category=cat, title=title, description=desc, icon=icon, order=order)
        self.stdout.write('  %d Gallery items created.' % len(items))

    def _seed_articles(self):
        if ArticleCategory.objects.exists():
            self.stdout.write('  ArticleCategory already exists, skipping.')
            return
        cats = [
            'Tips & Trik',
            'Perawatan',
            'Info Teknologi',
            'Panduan Beli',
        ]
        for name in cats:
            ArticleCategory.objects.create(name=name)
        self.stdout.write('  %d ArticleCategories created.' % len(cats))

        articles = [
            {
                'title': '5 Tanda Laptop Perlu Dibersihkan',
                'category': 'Perawatan',
                'excerpt': 'Laptop terasa semakin panas? Kipas berbunyi kasar? Bisa jadi debu sudah menumpuk di dalam. Yuk kenali tanda-tandanya.',
                'content': '<p>Laptop yang jarang dibersihkan bagian dalamnya bisa mengalami overheating, performa turun, bahkan kerusakan permanen pada komponen. Berikut 5 tanda laptop Anda perlu segera dibersihkan:</p><ol><li><strong>Kipas berbunyi kasar atau bising</strong> — debu yang menumpuk di kipas membuatnya tidak seimbang dan berisik.</li><li><strong>Suhu laptop panas berlebihan</strong> — ventilasi tersumbat debu membuat udara panas tidak bisa keluar.</li><li><strong>Performa menurun drastis</strong> — laptop sengaja menurunkan kecepatan prosesor (throttling) untuk mengurangi suhu.</li><li><strong>Sering mati mendadak</strong> — proteksi otomatis saat suhu sudah terlalu tinggi.</li><li><strong>Debu keluar dari ventilasi</strong> — tanda jelas bahwa bagian dalam sudah penuh debu.</li></ol><p>Bawa laptop Anda ke <strong>Zona Komputer Bojonegoro</strong> untuk pembersihan profesional. Kami buka casing, bersihkan kipas, heatsink, dan ganti thermal paste — laptop kembali dingin dan kencang.</p>',
                'icon': '🧹',
                'is_featured': True,
                'order': 1,
            },
            {
                'title': 'Panduan Memilih Laptop untuk Mahasiswa',
                'category': 'Panduan Beli',
                'excerpt': 'Bingung milih laptop buat kuliah? Simak panduan lengkap dari kami — mulai budget, spesifikasi minimal, hingga rekomendasi merek.',
                'content': '<p>Memilih laptop untuk kebutuhan kuliah memang membingungkan — apalagi dengan banyaknya pilihan di pasaran. Berikut panduan praktis dari tim Zona Komputer:</p><p><strong>Budget 3-5 Juta:</strong> Cari laptop second berkualitas seperti ThinkPad atau EliteBook. Spek minimal: Intel i5 gen 8, 8GB RAM, 256GB SSD. Cukup untuk tugas, browsing, dan Microsoft Office.</p><p><strong>Budget 5-8 Juta:</strong> Bisa dapat laptop baru entry-level seperti ASUS VivoBook, Lenovo IdeaPad, atau Acer Aspire. Spek: i5/Ryzen 5, 8GB RAM, 512GB SSD.</p><p><strong>Budget 8-12 Juta:</strong> Laptop mid-range untuk kebutuhan desain atau programming. Spek lebih tinggi, layar lebih baik, baterai lebih awet.</p><p><strong>Tips penting:</strong> Prioritaskan SSD, minimal 8GB RAM, dan prosesor minimal i5/Ryzen 5 generasi terbaru. Jangan tergiur harga murah dengan spek rendah — performa akan mengecewakan dalam 1-2 tahun.</p>',
                'icon': '🎓',
                'is_featured': False,
                'order': 2,
            },
            {
                'title': 'Cara Mengatasi Blue Screen di Windows',
                'category': 'Tips & Trik',
                'excerpt': 'Blue Screen of Death (BSOD) bikin panik? Tenang, banyak penyebabnya bisa diatasi sendiri sebelum bawa ke tukang servis.',
                'content': '<p>Blue Screen atau BSOD adalah layar biru yang muncul saat Windows mengalami error fatal. Berikut langkah-langkah yang bisa Anda coba:</p><p><strong>1. Catat kode error-nya.</strong> Biasanya ada tulisan seperti "CRITICAL_PROCESS_DIED" atau "MEMORY_MANAGEMENT". Kode ini penting untuk diagnosa.</p><p><strong>2. Restart laptop.</strong> Kadang BSOD terjadi sekali saja karena update Windows yang kurang sempurna. Jika tidak muncul lagi, tidak perlu khawatir.</p><p><strong>3. Update driver.</strong> Driver yang bermasalah (terutama driver VGA) sering jadi penyebab BSOD. Update driver melalui Device Manager.</p><p><strong>4. Cek RAM.</strong> RAM rusak atau kendor sering menyebabkan BSOD. Coba lepas dan pasang kembali RAM, atau gunakan tool Windows Memory Diagnostic.</p><p><strong>5. Scan hard drive.</strong> Buka Command Prompt sebagai Administrator, ketik <code>chkdsk /f /r</code> dan restart.</p><p>Jika BSOD terus muncul setelah mencoba langkah di atas, segera bawa ke <strong>Zona Komputer Bojonegoro</strong> untuk diagnosa lebih lanjut.</p>',
                'icon': '🖥️',
                'is_featured': False,
                'order': 3,
            },
            {
                'title': 'SSD vs HDD: Mana yang Cocok untuk Anda?',
                'category': 'Info Teknologi',
                'excerpt': 'Masih bingung beda SSD dan HDD? Simak perbandingan lengkap dari segi kecepatan, harga, dan ketahanan.',
                'content': '<p><strong>SSD (Solid State Drive)</strong> dan <strong>HDD (Hard Disk Drive)</strong> adalah dua jenis media penyimpanan yang sangat berbeda. Mana yang cocok untuk Anda?</p><p><strong>Kecepatan:</strong> SSD bisa 10-20x lebih cepat dari HDD. Booting Windows di SSD 10-15 detik, di HDD bisa 1-2 menit. Membuka aplikasi berat juga jauh lebih cepat di SSD.</p><p><strong>Harga:</strong> HDD masih jauh lebih murah per GB. SSD 500GB sekitar Rp 500-700rb, sedangkan HDD 1TB hanya Rp 300-400rb.</p><p><strong>Ketahanan:</strong> SSD lebih tahan guncangan karena tidak ada komponen bergerak. HDD mudah rusak jika terjatuh saat sedang bekerja.</p><p><strong>Rekomendasi:</strong> Untuk laptop utama, pilih SSD minimal 256GB. Untuk storage tambahan / backup, HDD masih pilihan ekonomis. Atau kombinasi keduanya: SSD untuk sistem + aplikasi, HDD untuk data.</p>',
                'icon': '💾',
                'is_featured': False,
                'order': 4,
            },
        ]
        for a in articles:
            cat = ArticleCategory.objects.get(name=a['category'])
            Article.objects.create(
                title=a['title'], category=cat, excerpt=a['excerpt'],
                content=a['content'], icon=a['icon'],
                is_featured=a['is_featured'], is_published=True,
                published_at=timezone.now(),
            )
        self.stdout.write('  %d Articles created.' % len(articles))

    def _seed_branches(self):
        if Branch.objects.exists():
            self.stdout.write('  Branch already exists, skipping.')
            return
        Branch.objects.create(
            name='Zona Komputer Pusat',
            address='Jl. Veteran No. 10, Bojonegoro',
            manager='Hadi',
            phone='0821-4060-3875',
            email='zonakomputer.bojonegoro@gmail.com',
            is_active=True,
        )
        self.stdout.write('  Branch created.')
