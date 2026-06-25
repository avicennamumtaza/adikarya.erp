from django.db import models
from django.utils.text import slugify
from apps.common.models import TimeStampedModel


class CompanyProfile(TimeStampedModel):
    name = models.CharField(max_length=100, default="Adikarya")
    short_description = models.TextField(blank=True)
    about_text = models.TextField(blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    whatsapp = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    operational_hours = models.CharField(max_length=100, blank=True)
    maps_url = models.URLField(blank=True, max_length=500)

    instagram_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)
    tiktok_url = models.URLField(blank=True)

    visi = models.TextField(blank=True)
    misi = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Company Profile"

    def __str__(self):
        return self.name


class CompanyStat(TimeStampedModel):
    title = models.CharField(max_length=50)
    value = models.CharField(max_length=50)
    description = models.CharField(max_length=100, blank=True)
    icon = models.CharField(max_length=20, blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.title} - {self.value}"


class CompanyValue(TimeStampedModel):
    title = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=20, blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title


class TickerText(TimeStampedModel):
    text = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.text


class TeamMember(TimeStampedModel):
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=100)
    specialty = models.CharField(max_length=100, blank=True)
    experience = models.CharField(max_length=50, blank=True)
    photo = models.ImageField(upload_to='team/', blank=True, null=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name


class PartnerBrand(TimeStampedModel):
    name = models.CharField(max_length=50)
    logo = models.ImageField(upload_to='brands/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name


class FAQ(TimeStampedModel):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.question


class Testimonial(TimeStampedModel):
    customer_name = models.CharField(max_length=100)
    customer_role = models.CharField(max_length=100, blank=True)
    content = models.TextField()
    rating = models.IntegerField(default=5)
    avatar_initial = models.CharField(max_length=2, blank=True)
    is_featured = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.customer_name} - {self.rating} Stars"


class Promo(TimeStampedModel):
    title = models.CharField(max_length=150)
    category = models.CharField(max_length=50, blank=True)
    description = models.TextField()
    benefits = models.TextField(blank=True, help_text="Satu benefit per baris")
    discount_text = models.CharField(max_length=100, blank=True)
    call_to_action = models.CharField(max_length=50, default="Klaim Promo ini")
    wa_text = models.CharField(max_length=200, blank=True)
    image = models.ImageField(upload_to='promos/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title


class GalleryCategory(TimeStampedModel):
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True, blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = "Gallery Categories"
        ordering = ['order']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Gallery(TimeStampedModel):
    category = models.ForeignKey(
        GalleryCategory, on_delete=models.CASCADE, related_name='items')
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=20, blank=True)
    image = models.ImageField(upload_to='gallery/', blank=True, null=True)
    order = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = "Galleries"
        ordering = ['order']

    def __str__(self):
        return self.title


class ArticleCategory(TimeStampedModel):
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True, blank=True)

    class Meta:
        verbose_name_plural = "Article Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Article(TimeStampedModel):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    category = models.ForeignKey(
        ArticleCategory, on_delete=models.SET_NULL, null=True, related_name='articles')
    excerpt = models.TextField(blank=True)
    content = models.TextField()
    icon = models.CharField(max_length=20, blank=True)
    image = models.ImageField(upload_to='articles/', blank=True, null=True)
    is_featured = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-published_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class ContactMessage(TimeStampedModel):
    name = models.CharField(max_length=100)
    contact_info = models.CharField(max_length=100)
    subject = models.CharField(max_length=100)
    message = models.TextField()
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {self.subject}"
