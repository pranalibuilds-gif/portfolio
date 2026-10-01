import re
import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower
from django.utils import timezone


def media_upload_path(instance, filename):
    extension = Path(filename).suffix.lower()
    if not re.fullmatch(r'\.[a-z0-9]{1,10}', extension):
        extension = ''
    return f'content/media/{uuid.uuid4().hex}{extension}'


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class PublishableModel(TimestampedModel):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='%(app_label)s_%(class)s_created',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='%(app_label)s_%(class)s_updated',
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=['draft', 'published']),
                name='%(app_label)s_%(class)s_valid_status',
            ),
            models.CheckConstraint(
                condition=Q(status='draft') | Q(published_at__isnull=False),
                name='%(app_label)s_%(class)s_pub_has_date',
            ),
        ]
        indexes = [
            models.Index(
                fields=['status', 'published_at'],
                name='%(app_label)s_%(class)s_pub_idx',
            ),
        ]

    def publish(self):
        self.status = self.Status.PUBLISHED
        self.published_at = timezone.now()

    def unpublish(self):
        self.status = self.Status.DRAFT


class Media(TimestampedModel):
    class Kind(models.TextChoices):
        IMAGE = 'image', 'Image'
        DOCUMENT = 'document', 'Document'

    file = models.FileField(upload_to=media_upload_path)
    kind = models.CharField(max_length=12, choices=Kind.choices)
    original_filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=255)
    size_bytes = models.PositiveBigIntegerField()
    alt_text = models.CharField(max_length=255, blank=True)
    caption = models.CharField(max_length=500, blank=True)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    checksum = models.CharField(max_length=64, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='uploaded_content_media',
    )

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=Q(kind__in=['image', 'document']),
                name='content_media_valid_kind',
            ),
            models.CheckConstraint(
                condition=Q(size_bytes__gt=0),
                name='content_media_positive_size',
            ),
            models.CheckConstraint(
                condition=Q(width__isnull=True) | Q(width__gt=0),
                name='content_media_positive_width',
            ),
            models.CheckConstraint(
                condition=Q(height__isnull=True) | Q(height__gt=0),
                name='content_media_positive_height',
            ),
        ]

    def __str__(self):
        return self.original_filename


class Profile(PublishableModel):
    singleton_key = models.PositiveSmallIntegerField(default=1, unique=True)
    name = models.CharField(max_length=160)
    headline = models.CharField(max_length=200)
    short_bio = models.CharField(max_length=500, blank=True)
    biography = models.TextField(blank=True)
    email = models.EmailField(blank=True)
    location = models.CharField(max_length=160, blank=True)
    avatar = models.ForeignKey(
        Media,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='profile_avatars',
    )

    class Meta(PublishableModel.Meta):
        ordering = ['singleton_key']
        constraints = [
            *PublishableModel.Meta.constraints,
            models.CheckConstraint(
                condition=Q(singleton_key=1),
                name='content_profile_singleton_key',
            ),
        ]

    def clean(self):
        super().clean()
        if self.avatar_id and self.avatar.kind != Media.Kind.IMAGE:
            raise ValidationError({'avatar': 'Profile avatars must be image media.'})

    def __str__(self):
        return self.name


class SkillCategory(TimestampedModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=110, unique=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'name']
        constraints = [
            models.UniqueConstraint(
                Lower('name'),
                name='content_skillcategory_name_ci_uniq',
            ),
        ]

    def __str__(self):
        return self.name


class Skill(PublishableModel):
    class SkillType(models.TextChoices):
        TECHNICAL = 'technical', 'Technical'
        TOOL = 'tool', 'Tool'
        SOFT = 'soft', 'Soft'

    name = models.CharField(max_length=100)
    skill_type = models.CharField(
        max_length=12,
        choices=SkillType.choices,
        default=SkillType.TECHNICAL,
    )
    category = models.ForeignKey(
        SkillCategory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='skills',
    )
    proficiency = models.PositiveSmallIntegerField(null=True, blank=True)
    icon = models.CharField(max_length=80, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta(PublishableModel.Meta):
        ordering = ['sort_order', 'name']
        constraints = [
            *PublishableModel.Meta.constraints,
            models.UniqueConstraint(Lower('name'), name='content_skill_name_ci_uniq'),
            models.CheckConstraint(
                condition=Q(skill_type__in=['technical', 'tool', 'soft']),
                name='content_skill_valid_type',
            ),
            models.CheckConstraint(
                condition=Q(proficiency__isnull=True)
                | Q(proficiency__range=(1, 5)),
                name='content_skill_proficiency_range',
            ),
        ]

    def __str__(self):
        return self.name


class Project(PublishableModel):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    summary = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    role = models.CharField(max_length=160, blank=True)
    project_url = models.URLField(blank=True)
    source_url = models.URLField(blank=True)
    started_on = models.DateField(null=True, blank=True)
    completed_on = models.DateField(null=True, blank=True)
    featured = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    cover_media = models.ForeignKey(
        Media,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='project_covers',
    )
    skills = models.ManyToManyField(Skill, blank=True, related_name='projects')
    gallery_media = models.ManyToManyField(
        Media,
        blank=True,
        through='ProjectMedia',
        related_name='gallery_projects',
    )

    class Meta(PublishableModel.Meta):
        ordering = ['-featured', 'sort_order', '-published_at', 'title']
        constraints = [
            *PublishableModel.Meta.constraints,
            models.CheckConstraint(
                condition=Q(completed_on__isnull=True)
                | Q(started_on__isnull=True)
                | Q(completed_on__gte=F('started_on')),
                name='content_project_dates_ordered',
            ),
        ]
        indexes = [
            *PublishableModel.Meta.indexes,
            models.Index(
                fields=['status', 'featured', 'sort_order'],
                name='content_project_list_idx',
            ),
        ]

    def clean(self):
        super().clean()
        if self.cover_media_id and self.cover_media.kind != Media.Kind.IMAGE:
            raise ValidationError({'cover_media': 'Project covers must be image media.'})

    def __str__(self):
        return self.title


class ProjectMedia(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='media_links',
    )
    media = models.ForeignKey(
        Media,
        on_delete=models.PROTECT,
        related_name='project_links',
    )
    position = models.PositiveIntegerField(default=0)
    caption = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ['position', 'pk']
        constraints = [
            models.UniqueConstraint(
                fields=['project', 'media'],
                name='content_projectmedia_pair_uniq',
            ),
            models.UniqueConstraint(
                fields=['project', 'position'],
                name='content_projectmedia_position_uniq',
            ),
        ]

    def clean(self):
        super().clean()
        if self.media_id and self.media.kind != Media.Kind.IMAGE:
            raise ValidationError({'media': 'Project gallery entries must be image media.'})

    def __str__(self):
        return f'{self.project}: {self.media}'


class Experience(PublishableModel):
    role = models.CharField(max_length=200)
    organization = models.CharField(max_length=200)
    location = models.CharField(max_length=160, blank=True)
    employment_type = models.CharField(max_length=40, blank=True)
    description = models.TextField(blank=True)
    started_on = models.DateField()
    ended_on = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta(PublishableModel.Meta):
        ordering = ['-is_current', '-started_on', 'sort_order']
        constraints = [
            *PublishableModel.Meta.constraints,
            models.CheckConstraint(
                condition=Q(ended_on__isnull=True)
                | Q(ended_on__gte=F('started_on')),
                name='content_experience_dates_ordered',
            ),
            models.CheckConstraint(
                condition=Q(is_current=False) | Q(ended_on__isnull=True),
                name='content_experience_current_no_end',
            ),
        ]

    def __str__(self):
        return f'{self.role} at {self.organization}'


class Education(PublishableModel):
    institution = models.CharField(max_length=200)
    degree = models.CharField(max_length=160)
    field_of_study = models.CharField(max_length=160, blank=True)
    location = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True)
    started_on = models.DateField(null=True, blank=True)
    ended_on = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta(PublishableModel.Meta):
        ordering = ['-is_current', '-ended_on', '-started_on', 'sort_order']
        constraints = [
            *PublishableModel.Meta.constraints,
            models.CheckConstraint(
                condition=Q(ended_on__isnull=True)
                | Q(started_on__isnull=True)
                | Q(ended_on__gte=F('started_on')),
                name='content_education_dates_ordered',
            ),
            models.CheckConstraint(
                condition=Q(is_current=False) | Q(ended_on__isnull=True),
                name='content_education_current_no_end',
            ),
        ]

    def __str__(self):
        return f'{self.degree} — {self.institution}'


class Service(PublishableModel):
    title = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    description = models.TextField()
    icon = models.CharField(max_length=80, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta(PublishableModel.Meta):
        ordering = ['sort_order', 'title']

    def __str__(self):
        return self.title


class Testimonial(PublishableModel):
    person_name = models.CharField(max_length=160)
    person_title = models.CharField(max_length=160, blank=True)
    organization = models.CharField(max_length=160, blank=True)
    quote = models.TextField()
    avatar = models.ForeignKey(
        Media,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='testimonial_avatars',
    )
    featured = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta(PublishableModel.Meta):
        ordering = ['-featured', 'sort_order', 'person_name']

    def clean(self):
        super().clean()
        if self.avatar_id and self.avatar.kind != Media.Kind.IMAGE:
            raise ValidationError({'avatar': 'Testimonial avatars must be image media.'})

    def __str__(self):
        return self.person_name


class BlogPost(PublishableModel):
    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, unique=True)
    excerpt = models.CharField(max_length=500)
    body_markdown = models.TextField()
    cover_media = models.ForeignKey(
        Media,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='blog_covers',
    )
    seo_title = models.CharField(max_length=70, blank=True)
    seo_description = models.CharField(max_length=180, blank=True)

    class Meta(PublishableModel.Meta):
        ordering = ['-published_at', 'title']

    def __str__(self):
        return self.title


class SocialLink(PublishableModel):
    platform = models.CharField(max_length=60)
    label = models.CharField(max_length=100)
    url = models.URLField(max_length=500)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta(PublishableModel.Meta):
        ordering = ['sort_order', 'platform']
        constraints = [
            *PublishableModel.Meta.constraints,
            models.UniqueConstraint(Lower('url'), name='content_social_url_ci_uniq'),
        ]

    def __str__(self):
        return self.label


class Resume(PublishableModel):
    title = models.CharField(max_length=160)
    file = models.ForeignKey(
        Media,
        on_delete=models.PROTECT,
        related_name='resume_versions',
    )
    is_current = models.BooleanField(default=False)

    class Meta(PublishableModel.Meta):
        ordering = ['-is_current', '-published_at', '-created_at']
        constraints = [
            *PublishableModel.Meta.constraints,
            models.UniqueConstraint(
                fields=['is_current'],
                condition=Q(status='published', is_current=True),
                name='content_resume_current_pub_uniq',
            ),
        ]

    def clean(self):
        super().clean()
        if self.file_id and self.file.kind != Media.Kind.DOCUMENT:
            raise ValidationError({'file': 'Resume files must be document media.'})

    def __str__(self):
        return self.title


class ContactMessage(TimestampedModel):
    class Status(models.TextChoices):
        NEW = 'new', 'New'
        READ = 'read', 'Read'
        REPLIED = 'replied', 'Replied'
        ARCHIVED = 'archived', 'Archived'

    name = models.CharField(max_length=160)
    email = models.EmailField()
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.NEW,
    )
    received_at = models.DateTimeField(default=timezone.now)
    read_at = models.DateTimeField(null=True, blank=True)
    replied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-received_at']
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=['new', 'read', 'replied', 'archived']),
                name='content_contact_valid_status',
            ),
        ]
        indexes = [
            models.Index(
                fields=['status', 'received_at'],
                name='content_contact_inbox_idx',
            ),
        ]

    def __str__(self):
        return f'{self.name} — {self.received_at:%Y-%m-%d %H:%M}'

# Create your models here.
