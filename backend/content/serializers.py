from pathlib import Path

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field

from .models import (
    BlogPost,
    ContactMessage,
    Education,
    Experience,
    Media,
    Profile,
    Project,
    ProjectMedia,
    PublishableModel,
    Resume,
    Service,
    Skill,
    SkillCategory,
    SocialLink,
    Testimonial,
)


class ModelValidationMixin:
    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = self.instance or self.Meta.model()
        for name, value in attrs.items():
            if name in {field.name for field in instance._meta.many_to_many}:
                continue
            setattr(instance, name, value)
        try:
            instance.full_clean(validate_unique=False)
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                getattr(error, 'message_dict', {'detail': error.messages})
            ) from error
        return attrs


class PublishableCMSSerializer(ModelValidationMixin, serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        read_only_fields = (
            'created_at',
            'updated_at',
            'created_by',
            'updated_by',
            'published_at',
            'status',
        )


class PublicMediaSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Media
        fields = ('id', 'file_url', 'kind', 'original_filename', 'alt_text', 'caption')

    @extend_schema_field(OpenApiTypes.URI)
    def get_file_url(self, obj):
        if not obj.file:
            return None
        url = obj.file.url
        request = self.context.get('request')
        return request.build_absolute_uri(url) if request else url


class ProfilePublicSerializer(serializers.ModelSerializer):
    avatar = PublicMediaSerializer(read_only=True)

    class Meta:
        model = Profile
        fields = (
            'id',
            'name',
            'headline',
            'short_bio',
            'biography',
            'email',
            'location',
            'avatar',
            'published_at',
        )


class SkillPublicSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()

    class Meta:
        model = Skill
        fields = ('id', 'name', 'skill_type', 'category', 'proficiency', 'icon')


class SkillCategoryPublicSerializer(serializers.ModelSerializer):
    skills = SkillPublicSerializer(many=True, read_only=True)

    class Meta:
        model = SkillCategory
        fields = ('id', 'name', 'slug', 'sort_order', 'skills')


class ProjectGalleryItemSerializer(serializers.ModelSerializer):
    media = PublicMediaSerializer(read_only=True)

    class Meta:
        model = ProjectMedia
        fields = ('media', 'position', 'caption')


class ProjectPublicSerializer(serializers.ModelSerializer):
    cover_media = PublicMediaSerializer(read_only=True)
    skills = SkillPublicSerializer(many=True, read_only=True)
    gallery_media = ProjectGalleryItemSerializer(source='media_links', many=True, read_only=True)

    class Meta:
        model = Project
        fields = (
            'id',
            'title',
            'slug',
            'summary',
            'description',
            'role',
            'project_url',
            'source_url',
            'started_on',
            'completed_on',
            'featured',
            'cover_media',
            'skills',
            'gallery_media',
            'published_at',
        )


class ExperiencePublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experience
        fields = (
            'id',
            'role',
            'organization',
            'location',
            'employment_type',
            'description',
            'started_on',
            'ended_on',
            'is_current',
        )


class EducationPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = (
            'id',
            'institution',
            'degree',
            'field_of_study',
            'location',
            'description',
            'started_on',
            'ended_on',
            'is_current',
        )


class ServicePublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ('id', 'title', 'slug', 'description', 'icon')


class TestimonialPublicSerializer(serializers.ModelSerializer):
    avatar = PublicMediaSerializer(read_only=True)

    class Meta:
        model = Testimonial
        fields = (
            'id',
            'person_name',
            'person_title',
            'organization',
            'quote',
            'avatar',
            'featured',
        )


class BlogPostPublicSerializer(serializers.ModelSerializer):
    cover_media = PublicMediaSerializer(read_only=True)

    class Meta:
        model = BlogPost
        fields = (
            'id',
            'title',
            'slug',
            'excerpt',
            'body_markdown',
            'cover_media',
            'seo_title',
            'seo_description',
            'published_at',
        )


class SocialLinkPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialLink
        fields = ('id', 'platform', 'label', 'url')


class ResumePublicSerializer(serializers.ModelSerializer):
    file = PublicMediaSerializer(read_only=True)

    class Meta:
        model = Resume
        fields = ('id', 'title', 'file', 'is_current', 'published_at')


class ProjectCMSSerializer(PublishableCMSSerializer):
    gallery_media = serializers.SerializerMethodField()
    gallery_media_ids = serializers.PrimaryKeyRelatedField(
        source='gallery_media',
        queryset=Media.objects.filter(kind=Media.Kind.IMAGE),
        many=True,
        required=False,
        write_only=True,
    )

    class Meta(PublishableCMSSerializer.Meta):
        model = Project

    def validate(self, attrs):
        start = attrs.get('started_on', getattr(self.instance, 'started_on', None))
        end = attrs.get('completed_on', getattr(self.instance, 'completed_on', None))
        if start and end and end < start:
            raise serializers.ValidationError(
                {'completed_on': 'The completion date must not be before the start date.'}
            )
        return super().validate(attrs)

    @extend_schema_field(ProjectGalleryItemSerializer(many=True))
    def get_gallery_media(self, obj):
        links = getattr(obj, 'media_links', None)
        if links is None:
            links = obj.media_links.select_related('media')
        return ProjectGalleryItemSerializer(links, many=True, context=self.context).data

    @transaction.atomic
    def create(self, validated_data):
        gallery = validated_data.pop('gallery_media', [])
        project = super().create(validated_data)
        for position, media in enumerate(gallery):
            ProjectMedia.objects.create(project=project, media=media, position=position)
        return project

    @transaction.atomic
    def update(self, instance, validated_data):
        gallery = validated_data.pop('gallery_media', serializers.empty)
        project = super().update(instance, validated_data)
        if gallery is not serializers.empty:
            requested_ids = {media.pk for media in gallery}
            project.media_links.exclude(media_id__in=requested_ids).delete()
            existing = {link.media_id: link for link in project.media_links.all()}
            current_max = (
                project.media_links.aggregate(max_position=Max('position'))['max_position']
                or 0
            )
            for offset, link in enumerate(existing.values(), start=1):
                link.position = current_max + offset
                link.save(update_fields=['position'])
            for position, media in enumerate(gallery):
                link = existing.get(media.pk)
                if link:
                    link.position = position
                    link.save(update_fields=['position'])
                else:
                    ProjectMedia.objects.create(
                        project=project,
                        media=media,
                        position=position,
                    )
            if hasattr(project, '_prefetched_objects_cache'):
                project._prefetched_objects_cache.pop('media_links', None)
        return project


class SkillCMSSerializer(PublishableCMSSerializer):
    class Meta(PublishableCMSSerializer.Meta):
        model = Skill


class SkillCategoryCMSSerializer(ModelValidationMixin, serializers.ModelSerializer):
    class Meta:
        model = SkillCategory
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class ProfileCMSSerializer(PublishableCMSSerializer):
    class Meta(PublishableCMSSerializer.Meta):
        model = Profile
        read_only_fields = PublishableCMSSerializer.Meta.read_only_fields + ('singleton_key',)

    def validate(self, attrs):
        if self.instance is None and Profile.objects.exists():
            raise serializers.ValidationError(
                {'detail': 'Only one profile can be managed; edit the existing profile.'}
            )
        return super().validate(attrs)


MAX_MEDIA_UPLOAD_BYTES = 10 * 1024 * 1024
MEDIA_SIGNATURES = (
    (b'\x89PNG\r\n\x1a\n', 'image/png', {'.png'}),
    (b'\xff\xd8\xff', 'image/jpeg', {'.jpg', '.jpeg'}),
    (b'GIF87a', 'image/gif', {'.gif'}),
    (b'GIF89a', 'image/gif', {'.gif'}),
    (b'RIFF', 'image/webp', {'.webp'}),
    (b'%PDF-', 'application/pdf', {'.pdf'}),
)


def media_file_type(upload):
    position = upload.tell()
    signature = upload.read(12)
    upload.seek(position)
    for prefix, mime_type, extensions in MEDIA_SIGNATURES:
        if signature.startswith(prefix):
            if mime_type == 'image/webp' and signature[8:12] != b'WEBP':
                continue
            return mime_type, extensions
    return None, set()


class MediaCMSSerializer(ModelValidationMixin, serializers.ModelSerializer):
    upload = serializers.FileField(source='file', write_only=True, required=False)
    file_url = serializers.SerializerMethodField()
    original_filename = serializers.CharField(read_only=True)
    mime_type = serializers.CharField(read_only=True)
    size_bytes = serializers.IntegerField(read_only=True)
    checksum = serializers.CharField(read_only=True)
    uploaded_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Media
        fields = (
            'id',
            'upload',
            'file_url',
            'kind',
            'original_filename',
            'mime_type',
            'size_bytes',
            'alt_text',
            'caption',
            'width',
            'height',
            'checksum',
            'uploaded_by',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at')

    @extend_schema_field(OpenApiTypes.URI)
    def get_file_url(self, obj):
        if not obj.file:
            return None
        url = obj.file.url
        request = self.context.get('request')
        return request.build_absolute_uri(url) if request else url

    def validate(self, attrs):
        upload = attrs.get('file')
        kind = attrs.get('kind', getattr(self.instance, 'kind', None))
        if upload is not None:
            if not upload.size:
                raise serializers.ValidationError({'upload': 'Uploaded files must not be empty.'})
            if upload.size > MAX_MEDIA_UPLOAD_BYTES:
                raise serializers.ValidationError(
                    {'upload': 'Files must be 10 MB or smaller.'}
                )
            mime_type, extensions = media_file_type(upload)
            extension = Path(upload.name).suffix.lower()
            if mime_type is None:
                raise serializers.ValidationError(
                    {'upload': 'Use a PNG, JPEG, GIF, WebP, or PDF file.'}
                )
            if extension not in extensions:
                raise serializers.ValidationError(
                    {'upload': 'The file extension must match the file contents.'}
                )
            expected_kind = (
                Media.Kind.IMAGE if mime_type.startswith('image/')
                else Media.Kind.DOCUMENT
            )
            if kind != expected_kind:
                raise serializers.ValidationError(
                    {'kind': 'Choose a media type that matches the uploaded file.'}
                )
            attrs.update(
                original_filename=upload.name[:255],
                mime_type=mime_type[:255],
                size_bytes=upload.size,
            )
        elif self.instance is None:
            raise serializers.ValidationError({'upload': 'This field is required.'})
        elif kind != self.instance.kind:
            raise serializers.ValidationError(
                {'kind': 'Upload a new file to change its media type.'}
            )
        return super().validate(attrs)

    def create(self, validated_data):
        validated_data['uploaded_by'] = self.context['request'].user
        return super().create(validated_data)


class ContactPublicCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ('name', 'email', 'subject', 'message')

    def validate_name(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError('Enter at least 2 characters.')
        return value.strip()

    def validate_message(self, value):
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError('Enter at least 10 characters.')
        return value


class ContactSubmissionResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class ContactCMSSerializer(ModelValidationMixin, serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'received_at', 'read_at', 'replied_at')

    def update(self, instance, validated_data):
        next_status = validated_data.get('status', instance.status)
        now = timezone.now()
        if next_status in (ContactMessage.Status.READ, ContactMessage.Status.REPLIED):
            if instance.read_at is None:
                instance.read_at = now
        if next_status == ContactMessage.Status.REPLIED and instance.replied_at is None:
            instance.replied_at = now
        return super().update(instance, validated_data)


class OrderedDatesSerializerMixin:
    def validate(self, attrs):
        instance = self.instance

        def get_value(name):
            if name in attrs:
                return attrs[name]
            return getattr(instance, name, None) if instance else None

        start = get_value('started_on')
        end = get_value('ended_on')
        current = get_value('is_current')
        if start and end and end < start:
            raise serializers.ValidationError(
                {'ended_on': 'The end date must not be before the start date.'}
            )
        if current and end:
            raise serializers.ValidationError(
                {'ended_on': 'Current records must not have an end date.'}
            )
        return super().validate(attrs)


class ExperienceCMSSerializer(OrderedDatesSerializerMixin, PublishableCMSSerializer):
    class Meta(PublishableCMSSerializer.Meta):
        model = Experience


class EducationCMSSerializer(OrderedDatesSerializerMixin, PublishableCMSSerializer):
    class Meta(PublishableCMSSerializer.Meta):
        model = Education


class ServiceCMSSerializer(PublishableCMSSerializer):
    class Meta(PublishableCMSSerializer.Meta):
        model = Service


class TestimonialCMSSerializer(PublishableCMSSerializer):
    class Meta(PublishableCMSSerializer.Meta):
        model = Testimonial


class BlogPostCMSSerializer(PublishableCMSSerializer):
    class Meta(PublishableCMSSerializer.Meta):
        model = BlogPost

    def validate_cover_media(self, media):
        if media and media.kind != Media.Kind.IMAGE:
            raise serializers.ValidationError('Blog covers must be image media.')
        return media


class SocialLinkCMSSerializer(PublishableCMSSerializer):
    class Meta(PublishableCMSSerializer.Meta):
        model = SocialLink


class ResumeCMSSerializer(PublishableCMSSerializer):
    class Meta(PublishableCMSSerializer.Meta):
        model = Resume


class ProjectMediaCMSSerializer(ModelValidationMixin, serializers.ModelSerializer):
    class Meta:
        model = ProjectMedia
        fields = '__all__'
