from django import forms
from .models import (
    CompanyProfile, FAQ, Promo, CompanyStat, CompanyValue,
    TickerText, TeamMember, PartnerBrand, Testimonial,
    GalleryCategory, Gallery, ArticleCategory, Article
)

class CompanyProfileForm(forms.ModelForm):
    class Meta:
        model = CompanyProfile
        fields = '__all__'

class FAQForm(forms.ModelForm):
    class Meta:
        model = FAQ
        fields = '__all__'

class PromoForm(forms.ModelForm):
    class Meta:
        model = Promo
        fields = '__all__'

class CompanyStatForm(forms.ModelForm):
    class Meta:
        model = CompanyStat
        fields = '__all__'

class CompanyValueForm(forms.ModelForm):
    class Meta:
        model = CompanyValue
        fields = '__all__'

class TickerTextForm(forms.ModelForm):
    class Meta:
        model = TickerText
        fields = '__all__'

class TeamMemberForm(forms.ModelForm):
    class Meta:
        model = TeamMember
        fields = '__all__'

class PartnerBrandForm(forms.ModelForm):
    class Meta:
        model = PartnerBrand
        fields = '__all__'

class TestimonialForm(forms.ModelForm):
    class Meta:
        model = Testimonial
        fields = '__all__'

class GalleryCategoryForm(forms.ModelForm):
    class Meta:
        model = GalleryCategory
        fields = '__all__'

class GalleryForm(forms.ModelForm):
    class Meta:
        model = Gallery
        fields = '__all__'

class ArticleCategoryForm(forms.ModelForm):
    class Meta:
        model = ArticleCategory
        fields = '__all__'

class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = '__all__'
