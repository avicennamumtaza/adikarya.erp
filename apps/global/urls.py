from django.urls import path
from . import views

app_name = 'global'

urlpatterns = [
    path('', views.GlobalDashboardView.as_view(), name='dashboard'),
    path('company/', views.CompanyProfileUpdateView.as_view(), name='company_profile'),
    
    path('faq/', views.FAQListView.as_view(), name='faq_list'),
    path('faq/add/', views.FAQCreateView.as_view(), name='faq_add'),
    path('faq/<int:pk>/edit/', views.FAQUpdateView.as_view(), name='faq_edit'),
    path('faq/<int:pk>/delete/', views.FAQDeleteView.as_view(), name='faq_delete'),

    path('promo/', views.PromoListView.as_view(), name='promo_list'),
    path('promo/add/', views.PromoCreateView.as_view(), name='promo_add'),
    path('promo/<int:pk>/edit/', views.PromoUpdateView.as_view(), name='promo_edit'),
    path('promo/<int:pk>/delete/', views.PromoDeleteView.as_view(), name='promo_delete'),

    path('team/', views.TeamMemberListView.as_view(), name='team_list'),
    path('team/add/', views.TeamMemberCreateView.as_view(), name='team_add'),
    path('team/<int:pk>/edit/', views.TeamMemberUpdateView.as_view(), name='team_edit'),
    path('team/<int:pk>/delete/', views.TeamMemberDeleteView.as_view(), name='team_delete'),

    path('testimonial/', views.TestimonialListView.as_view(), name='testimonial_list'),
    path('testimonial/add/', views.TestimonialCreateView.as_view(), name='testimonial_add'),
    path('testimonial/<int:pk>/edit/', views.TestimonialUpdateView.as_view(), name='testimonial_edit'),
    path('testimonial/<int:pk>/delete/', views.TestimonialDeleteView.as_view(), name='testimonial_delete'),

    path('brand/', views.PartnerBrandListView.as_view(), name='brand_list'),
    path('brand/add/', views.PartnerBrandCreateView.as_view(), name='brand_add'),
    path('brand/<int:pk>/edit/', views.PartnerBrandUpdateView.as_view(), name='brand_edit'),
    path('brand/<int:pk>/delete/', views.PartnerBrandDeleteView.as_view(), name='brand_delete'),

    path('stat/', views.CompanyStatListView.as_view(), name='stat_list'),
    path('stat/add/', views.CompanyStatCreateView.as_view(), name='stat_add'),
    path('stat/<int:pk>/edit/', views.CompanyStatUpdateView.as_view(), name='stat_edit'),
    path('stat/<int:pk>/delete/', views.CompanyStatDeleteView.as_view(), name='stat_delete'),

    path('value/', views.CompanyValueListView.as_view(), name='value_list'),
    path('value/add/', views.CompanyValueCreateView.as_view(), name='value_add'),
    path('value/<int:pk>/edit/', views.CompanyValueUpdateView.as_view(), name='value_edit'),
    path('value/<int:pk>/delete/', views.CompanyValueDeleteView.as_view(), name='value_delete'),

    path('ticker/', views.TickerTextListView.as_view(), name='ticker_list'),
    path('ticker/add/', views.TickerTextCreateView.as_view(), name='ticker_add'),
    path('ticker/<int:pk>/edit/', views.TickerTextUpdateView.as_view(), name='ticker_edit'),
    path('ticker/<int:pk>/delete/', views.TickerTextDeleteView.as_view(), name='ticker_delete'),

    path('gallery/', views.GalleryListView.as_view(), name='gallery_list'),
    path('gallery/add/', views.GalleryCreateView.as_view(), name='gallery_add'),
    path('gallery/<int:pk>/edit/', views.GalleryUpdateView.as_view(), name='gallery_edit'),
    path('gallery/<int:pk>/delete/', views.GalleryDeleteView.as_view(), name='gallery_delete'),

    path('gallery-category/', views.GalleryCategoryListView.as_view(), name='gallery_category_list'),
    path('gallery-category/add/', views.GalleryCategoryCreateView.as_view(), name='gallery_category_add'),
    path('gallery-category/<int:pk>/edit/', views.GalleryCategoryUpdateView.as_view(), name='gallery_category_edit'),
    path('gallery-category/<int:pk>/delete/', views.GalleryCategoryDeleteView.as_view(), name='gallery_category_delete'),

    path('article/', views.ArticleListView.as_view(), name='article_list'),
    path('article/add/', views.ArticleCreateView.as_view(), name='article_add'),
    path('article/<int:pk>/edit/', views.ArticleUpdateView.as_view(), name='article_edit'),
    path('article/<int:pk>/delete/', views.ArticleDeleteView.as_view(), name='article_delete'),

    path('article-category/', views.ArticleCategoryListView.as_view(), name='article_category_list'),
    path('article-category/add/', views.ArticleCategoryCreateView.as_view(), name='article_category_add'),
    path('article-category/<int:pk>/edit/', views.ArticleCategoryUpdateView.as_view(), name='article_category_edit'),
    path('article-category/<int:pk>/delete/', views.ArticleCategoryDeleteView.as_view(), name='article_category_delete'),

    path('contact-message/', views.ContactMessageListView.as_view(), name='contact_message_list'),
    path('contact-message/<int:pk>/delete/', views.ContactMessageDeleteView.as_view(), name='contact_message_delete'),

    # ── Guest-facing pages ──
    path('pages/', views.HomeView.as_view(), name='home'),
    path('pages/tentang/', views.AboutView.as_view(), name='tentang'),
    path('pages/layanan/', views.ServicesView.as_view(), name='layanan'),
    path('pages/produk/', views.ProductsView.as_view(), name='produk'),
    path('pages/promo/', views.PromosView.as_view(), name='promo'),
    path('pages/galeri/', views.GalleryView.as_view(), name='galeri'),
    path('pages/testimoni/', views.TestimonialsView.as_view(), name='testimoni'),
    path('pages/blog/', views.BlogView.as_view(), name='blog'),
    path('pages/faq/', views.FaqView.as_view(), name='faq'),
    path('pages/kontak/', views.ContactView.as_view(), name='kontak'),
]
