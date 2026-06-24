import importlib
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView, FormView
from django.contrib import messages
from .models import (
    CompanyProfile, FAQ, Promo, CompanyStat, CompanyValue,
    TickerText, TeamMember, PartnerBrand, Testimonial,
    GalleryCategory, Gallery, ArticleCategory, Article, ContactMessage
)
# Use importlib for cross-app imports to avoid Python 3.12 SyntaxError
_im = importlib.import_module('apps.inventory.models')
Product = _im.Product
Stock = _im.Stock
from .forms import (
    CompanyProfileForm, FAQForm, PromoForm, CompanyStatForm, CompanyValueForm,
    TickerTextForm, TeamMemberForm, PartnerBrandForm, TestimonialForm,
    GalleryCategoryForm, GalleryForm, ArticleCategoryForm, ArticleForm
)

class GlobalDashboardView(TemplateView):
    template_name = 'global_admin/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['faq_count'] = FAQ.objects.count()
        context['promo_count'] = Promo.objects.count()
        context['team_count'] = TeamMember.objects.count()
        context['testimonial_count'] = Testimonial.objects.count()
        context['gallery_count'] = Gallery.objects.count()
        context['article_count'] = Article.objects.count()
        context['partner_brand_count'] = PartnerBrand.objects.count()
        context['company_stat_count'] = CompanyStat.objects.count()
        context['company_value_count'] = CompanyValue.objects.count()
        context['ticker_count'] = TickerText.objects.count()
        return context

class CompanyProfileUpdateView(UpdateView):
    model = CompanyProfile
    form_class = CompanyProfileForm
    template_name = 'global_admin/company_profile_form.html'
    success_url = reverse_lazy('global:dashboard')

    def get_object(self, queryset=None):
        obj, created = CompanyProfile.objects.get_or_create(id=1)
        return obj

    def form_valid(self, form):
        messages.success(self.request, "Company Profile updated successfully.")
        return super().form_valid(form)

# Base Mixin for Messages
class SuccessMessageMixin:
    success_message = ""
    def form_valid(self, form):
        messages.success(self.request, self.success_message)
        return super().form_valid(form)

# --- FAQ ---
class FAQListView(ListView):
    model = FAQ
    template_name = 'global_admin/faq_list.html'
    context_object_name = 'faqs'

class FAQCreateView(SuccessMessageMixin, CreateView):
    model = FAQ; form_class = FAQForm; template_name = 'global_admin/faq_form.html'; success_url = reverse_lazy('global:faq_list'); success_message = "FAQ created successfully."

class FAQUpdateView(SuccessMessageMixin, UpdateView):
    model = FAQ; form_class = FAQForm; template_name = 'global_admin/faq_form.html'; success_url = reverse_lazy('global:faq_list'); success_message = "FAQ updated successfully."

class FAQDeleteView(DeleteView):
    model = FAQ; success_url = reverse_lazy('global:faq_list')
    def delete(self, request, *args, **kwargs):
        messages.success(request, "FAQ deleted.")
        return super().delete(request, *args, **kwargs)

# --- Promo ---
class PromoListView(ListView):
    model = Promo; template_name = 'global_admin/promo_list.html'; context_object_name = 'promos'

class PromoCreateView(SuccessMessageMixin, CreateView):
    model = Promo; form_class = PromoForm; template_name = 'global_admin/promo_form.html'; success_url = reverse_lazy('global:promo_list'); success_message = "Promo created."

class PromoUpdateView(SuccessMessageMixin, UpdateView):
    model = Promo; form_class = PromoForm; template_name = 'global_admin/promo_form.html'; success_url = reverse_lazy('global:promo_list'); success_message = "Promo updated."

class PromoDeleteView(DeleteView):
    model = Promo; success_url = reverse_lazy('global:promo_list')
    def delete(self, request, *args, **kwargs):
        messages.success(request, "Promo deleted.")
        return super().delete(request, *args, **kwargs)

# --- TeamMember ---
class TeamMemberListView(ListView):
    model = TeamMember; template_name = 'global_admin/team_list.html'; context_object_name = 'items'

class TeamMemberCreateView(SuccessMessageMixin, CreateView):
    model = TeamMember; form_class = TeamMemberForm; template_name = 'global_admin/generic_form.html'; success_url = reverse_lazy('global:team_list'); success_message = "Team Member created."
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = "Add Team Member"; ctx['back_url'] = reverse_lazy('global:team_list')
        return ctx

class TeamMemberUpdateView(SuccessMessageMixin, UpdateView):
    model = TeamMember; form_class = TeamMemberForm; template_name = 'global_admin/generic_form.html'; success_url = reverse_lazy('global:team_list'); success_message = "Team Member updated."
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = "Edit Team Member"; ctx['back_url'] = reverse_lazy('global:team_list')
        return ctx

class TeamMemberDeleteView(DeleteView):
    model = TeamMember; success_url = reverse_lazy('global:team_list')

# --- Testimonial ---
class TestimonialListView(ListView):
    model = Testimonial; template_name = 'global_admin/testimonial_list.html'; context_object_name = 'items'

class TestimonialCreateView(SuccessMessageMixin, CreateView):
    model = Testimonial; form_class = TestimonialForm; template_name = 'global_admin/generic_form.html'; success_url = reverse_lazy('global:testimonial_list'); success_message = "Testimonial created."
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = "Add Testimonial"; ctx['back_url'] = reverse_lazy('global:testimonial_list')
        return ctx

class TestimonialUpdateView(SuccessMessageMixin, UpdateView):
    model = Testimonial; form_class = TestimonialForm; template_name = 'global_admin/generic_form.html'; success_url = reverse_lazy('global:testimonial_list'); success_message = "Testimonial updated."
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = "Edit Testimonial"; ctx['back_url'] = reverse_lazy('global:testimonial_list')
        return ctx

class TestimonialDeleteView(DeleteView):
    model = Testimonial; success_url = reverse_lazy('global:testimonial_list')

# --- PartnerBrand ---
class PartnerBrandListView(ListView):
    model = PartnerBrand; template_name = 'global_admin/partner_brand_list.html'; context_object_name = 'items'

class PartnerBrandCreateView(SuccessMessageMixin, CreateView):
    model = PartnerBrand; form_class = PartnerBrandForm; template_name = 'global_admin/generic_form.html'; success_url = reverse_lazy('global:brand_list'); success_message = "Partner Brand created."
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = "Add Partner Brand"; ctx['back_url'] = reverse_lazy('global:brand_list')
        return ctx

class PartnerBrandUpdateView(SuccessMessageMixin, UpdateView):
    model = PartnerBrand; form_class = PartnerBrandForm; template_name = 'global_admin/generic_form.html'; success_url = reverse_lazy('global:brand_list'); success_message = "Partner Brand updated."
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = "Edit Partner Brand"; ctx['back_url'] = reverse_lazy('global:brand_list')
        return ctx

class PartnerBrandDeleteView(DeleteView):
    model = PartnerBrand; success_url = reverse_lazy('global:brand_list')

# --- CompanyStat ---
class CompanyStatListView(ListView):
    model = CompanyStat; template_name = 'global_admin/company_stat_list.html'; context_object_name = 'items'

class CompanyStatCreateView(SuccessMessageMixin, CreateView):
    model = CompanyStat; form_class = CompanyStatForm; template_name = 'global_admin/generic_form.html'; success_url = reverse_lazy('global:stat_list'); success_message = "Company Stat created."
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = "Add Company Stat"; ctx['back_url'] = reverse_lazy('global:stat_list')
        return ctx

class CompanyStatUpdateView(SuccessMessageMixin, UpdateView):
    model = CompanyStat; form_class = CompanyStatForm; template_name = 'global_admin/generic_form.html'; success_url = reverse_lazy('global:stat_list'); success_message = "Company Stat updated."
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = "Edit Company Stat"; ctx['back_url'] = reverse_lazy('global:stat_list')
        return ctx

class CompanyStatDeleteView(DeleteView):
    model = CompanyStat; success_url = reverse_lazy('global:stat_list')

# --- CompanyValue ---
class CompanyValueListView(ListView):
    model = CompanyValue; template_name = 'global_admin/company_value_list.html'; context_object_name = 'items'

class CompanyValueCreateView(SuccessMessageMixin, CreateView):
    model = CompanyValue; form_class = CompanyValueForm; template_name = 'global_admin/generic_form.html'; success_url = reverse_lazy('global:value_list'); success_message = "Company Value created."
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = "Add Company Value"; ctx['back_url'] = reverse_lazy('global:value_list')
        return ctx

class CompanyValueUpdateView(SuccessMessageMixin, UpdateView):
    model = CompanyValue; form_class = CompanyValueForm; template_name = 'global_admin/generic_form.html'; success_url = reverse_lazy('global:value_list'); success_message = "Company Value updated."
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = "Edit Company Value"; ctx['back_url'] = reverse_lazy('global:value_list')
        return ctx

class CompanyValueDeleteView(DeleteView):
    model = CompanyValue; success_url = reverse_lazy('global:value_list')

# --- TickerText ---
class TickerTextListView(ListView):
    model = TickerText; template_name = 'global_admin/ticker_list.html'; context_object_name = 'items'

class TickerTextCreateView(SuccessMessageMixin, CreateView):
    model = TickerText; form_class = TickerTextForm; template_name = 'global_admin/generic_form.html'; success_url = reverse_lazy('global:ticker_list'); success_message = "Ticker Text created."
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = "Add Ticker Text"; ctx['back_url'] = reverse_lazy('global:ticker_list')
        return ctx

class TickerTextUpdateView(SuccessMessageMixin, UpdateView):
    model = TickerText; form_class = TickerTextForm; template_name = 'global_admin/generic_form.html'; success_url = reverse_lazy('global:ticker_list'); success_message = "Ticker Text updated."
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = "Edit Ticker Text"; ctx['back_url'] = reverse_lazy('global:ticker_list')
        return ctx

class TickerTextDeleteView(DeleteView):
    model = TickerText; success_url = reverse_lazy('global:ticker_list')

# --- Gallery ---
class GalleryListView(ListView):
    model = Gallery; template_name = 'global_admin/gallery_list.html'; context_object_name = 'items'

class GalleryCreateView(SuccessMessageMixin, CreateView):
    model = Gallery; form_class = GalleryForm; template_name = 'global_admin/generic_form.html'; success_url = reverse_lazy('global:gallery_list'); success_message = "Gallery created."
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = "Add Gallery Item"; ctx['back_url'] = reverse_lazy('global:gallery_list')
        return ctx

class GalleryUpdateView(SuccessMessageMixin, UpdateView):
    model = Gallery; form_class = GalleryForm; template_name = 'global_admin/generic_form.html'; success_url = reverse_lazy('global:gallery_list'); success_message = "Gallery updated."
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = "Edit Gallery Item"; ctx['back_url'] = reverse_lazy('global:gallery_list')
        return ctx

class GalleryDeleteView(DeleteView):
    model = Gallery; success_url = reverse_lazy('global:gallery_list')

# --- Gallery Category ---
class GalleryCategoryListView(ListView):
    model = GalleryCategory; template_name = 'global_admin/gallery_category_list.html'; context_object_name = 'items'

class GalleryCategoryCreateView(SuccessMessageMixin, CreateView):
    model = GalleryCategory; form_class = GalleryCategoryForm; template_name = 'global_admin/generic_form.html'; success_url = reverse_lazy('global:gallery_category_list'); success_message = "Category created."
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = "Add Gallery Category"; ctx['back_url'] = reverse_lazy('global:gallery_category_list')
        return ctx

class GalleryCategoryUpdateView(SuccessMessageMixin, UpdateView):
    model = GalleryCategory; form_class = GalleryCategoryForm; template_name = 'global_admin/generic_form.html'; success_url = reverse_lazy('global:gallery_category_list'); success_message = "Category updated."
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = "Edit Gallery Category"; ctx['back_url'] = reverse_lazy('global:gallery_category_list')
        return ctx

class GalleryCategoryDeleteView(DeleteView):
    model = GalleryCategory; success_url = reverse_lazy('global:gallery_category_list')

# --- Article ---
class ArticleListView(ListView):
    model = Article; template_name = 'global_admin/article_list.html'; context_object_name = 'items'

class ArticleCreateView(SuccessMessageMixin, CreateView):
    model = Article; form_class = ArticleForm; template_name = 'global_admin/generic_form.html'; success_url = reverse_lazy('global:article_list'); success_message = "Article created."
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = "Add Article"; ctx['back_url'] = reverse_lazy('global:article_list')
        return ctx

class ArticleUpdateView(SuccessMessageMixin, UpdateView):
    model = Article; form_class = ArticleForm; template_name = 'global_admin/generic_form.html'; success_url = reverse_lazy('global:article_list'); success_message = "Article updated."
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = "Edit Article"; ctx['back_url'] = reverse_lazy('global:article_list')
        return ctx

class ArticleDeleteView(DeleteView):
    model = Article; success_url = reverse_lazy('global:article_list')

# --- Article Category ---
class ArticleCategoryListView(ListView):
    model = ArticleCategory; template_name = 'global_admin/article_category_list.html'; context_object_name = 'items'

class ArticleCategoryCreateView(SuccessMessageMixin, CreateView):
    model = ArticleCategory; form_class = ArticleCategoryForm; template_name = 'global_admin/generic_form.html'; success_url = reverse_lazy('global:article_category_list'); success_message = "Category created."
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = "Add Article Category"; ctx['back_url'] = reverse_lazy('global:article_category_list')
        return ctx

class ArticleCategoryUpdateView(SuccessMessageMixin, UpdateView):
    model = ArticleCategory; form_class = ArticleCategoryForm; template_name = 'global_admin/generic_form.html'; success_url = reverse_lazy('global:article_category_list'); success_message = "Category updated."
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = "Edit Article Category"; ctx['back_url'] = reverse_lazy('global:article_category_list')
        return ctx

class ArticleCategoryDeleteView(DeleteView):
    model = ArticleCategory; success_url = reverse_lazy('global:article_category_list')

# --- ContactMessage ---
class ContactMessageListView(ListView):
    model = ContactMessage; template_name = 'global_admin/contact_message_list.html'; context_object_name = 'items'

class ContactMessageDeleteView(DeleteView):
    model = ContactMessage; success_url = reverse_lazy('global:contact_message_list')


# ═══════════════════════════════════════════════
# GUEST (PUBLIC-FACING) VIEWS
# ═══════════════════════════════════════════════

class GuestBaseMixin:
    """Mixin that provides common context for all guest pages."""

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['company'] = CompanyProfile.objects.first()
        return ctx


class HomeView(GuestBaseMixin, TemplateView):
    template_name = 'global/index.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_page'] = 'index'
        ctx['tickers'] = TickerText.objects.filter(is_active=True)
        ctx['stats'] = CompanyStat.objects.all()
        ctx['values'] = CompanyValue.objects.all()
        ctx['active_promos'] = Promo.objects.filter(is_active=True)[:6]
        ctx['featured_testimonials'] = Testimonial.objects.filter(is_featured=True)[:4]
        ctx['gallery_categories'] = GalleryCategory.objects.all()
        ctx['gallery_items'] = Gallery.objects.all()
        ctx['partner_brands'] = PartnerBrand.objects.filter(is_active=True)
        return ctx


class AboutView(GuestBaseMixin, TemplateView):
    template_name = 'global/tentang.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_page'] = 'tentang'
        ctx['stats'] = CompanyStat.objects.all()
        ctx['values'] = CompanyValue.objects.all()
        ctx['team_members'] = TeamMember.objects.all()
        ctx['partner_brands'] = PartnerBrand.objects.filter(is_active=True)
        return ctx


class ServicesView(GuestBaseMixin, TemplateView):
    template_name = 'global/layanan.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_page'] = 'layanan'
        return ctx


class ProductsView(GuestBaseMixin, TemplateView):
    template_name = 'global/produk.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_page'] = 'produk'
        products = Product.objects.filter(product_type='PRODUCT').order_by('category', 'name')
        ctx['products'] = products
        categories = (products.values_list('category', flat=True)
                      .distinct().order_by('category'))
        ctx['product_categories'] = [c for c in categories if c]
        return ctx


class PromosView(GuestBaseMixin, TemplateView):
    template_name = 'global/promo.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_page'] = 'promo'
        promos = Promo.objects.filter(is_active=True)
        for p in promos:
            if p.benefits:
                p.benefits_list = [ln.strip() for ln in p.benefits.split('\n') if ln.strip()]
            else:
                p.benefits_list = []
        ctx['active_promos'] = promos
        return ctx


class GalleryView(GuestBaseMixin, TemplateView):
    template_name = 'global/galeri.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_page'] = 'galeri'
        ctx['gallery_categories'] = GalleryCategory.objects.all()
        ctx['gallery_items'] = Gallery.objects.all()
        return ctx


class TestimonialsView(GuestBaseMixin, TemplateView):
    template_name = 'global/testimoni.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_page'] = 'testimoni'
        ctx['testimonials'] = Testimonial.objects.all()
        ctx['featured_testimonials'] = Testimonial.objects.filter(is_featured=True)
        return ctx


class BlogView(GuestBaseMixin, TemplateView):
    template_name = 'global/blog.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_page'] = 'blog'
        ctx['articles'] = Article.objects.filter(is_published=True)
        ctx['featured_article'] = Article.objects.filter(is_featured=True, is_published=True).first()
        ctx['categories'] = ArticleCategory.objects.all()
        return ctx


class FaqView(GuestBaseMixin, TemplateView):
    template_name = 'global/faq.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_page'] = 'faq'
        ctx['faqs'] = FAQ.objects.filter(is_active=True)
        return ctx


class ContactView(GuestBaseMixin, TemplateView):
    template_name = 'global/kontak.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_page'] = 'kontak'
        return ctx

    def post(self, request, *args, **kwargs):
        name = request.POST.get('name', '').strip()
        contact_info = request.POST.get('contact_info', '').strip()
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()
        if name and contact_info and subject and message:
            ContactMessage.objects.create(
                name=name, contact_info=contact_info,
                subject=subject, message=message
            )
            messages.success(request, 'Pesan berhasil dikirim! Kami akan menghubungi Anda segera.')
        else:
            messages.error(request, 'Harap isi semua bidang yang wajib diisi.')
        return redirect('global:kontak')
