from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Prefetch
from django.db.models.deletion import ProtectedError
from rest_framework import filters, generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.throttling import AnonRateThrottle
from drf_spectacular.utils import extend_schema, extend_schema_view

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
from .serializers import (
    BlogPostPublicSerializer,
    BlogPostCMSSerializer,
    ContactCMSSerializer,
    ContactPublicCreateSerializer,
    ContactSubmissionResponseSerializer,
    EducationCMSSerializer,
    EducationPublicSerializer,
    ExperienceCMSSerializer,
    ExperiencePublicSerializer,
    MediaCMSSerializer,
    ProfileCMSSerializer,
    ProfilePublicSerializer,
    ProjectCMSSerializer,
    ProjectPublicSerializer,
    ProjectMediaCMSSerializer,
    ResumeCMSSerializer,
    ResumePublicSerializer,
    ServiceCMSSerializer,
    ServicePublicSerializer,
    SkillCMSSerializer,
    SkillCategoryCMSSerializer,
    SkillCategoryPublicSerializer,
    SkillPublicSerializer,
    SocialLinkCMSSerializer,
    SocialLinkPublicSerializer,
    TestimonialCMSSerializer,
    TestimonialPublicSerializer,
)


class ContentPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class QueryParameterFiltersMixin:
    filter_fields = {}
    boolean_filter_fields = ()

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        for parameter, field in self.filter_fields.items():
            value = self.request.query_params.get(parameter)
            if value is None:
                continue
            if parameter in self.boolean_filter_fields:
                if value.lower() not in ('true', 'false'):
                    raise ValidationError({parameter: 'Use true or false.'})
                value = value.lower() == 'true'
            try:
                queryset = queryset.filter(**{field: value})
            except (ValueError, DjangoValidationError) as error:
                raise ValidationError({parameter: 'Invalid filter value.'}) from error
        return queryset


@extend_schema_view(
    list=extend_schema(tags=('Public content',)),
    retrieve=extend_schema(tags=('Public content',)),
)
class PublicContentViewSet(QueryParameterFiltersMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = (AllowAny,)
    pagination_class = ContentPagination
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    ordering_fields = ()
    lookup_field = 'pk'
    queryset = None
    serializer_class = None

    def get_queryset(self):
        return self.queryset.filter(status=PublishableModel.Status.PUBLISHED)


class ProfilePublicView(generics.RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ProfilePublicSerializer
    queryset = Profile.objects.filter(status=PublishableModel.Status.PUBLISHED)

    def get_object(self):
        return self.get_queryset().select_related('avatar').first() or self.raise_not_found()

    @staticmethod
    def raise_not_found():
        raise NotFound('No published profile is available.')


class PublicSkillViewSet(PublicContentViewSet):
    queryset = Skill.objects.select_related('category')
    serializer_class = SkillPublicSerializer
    search_fields = ('name', 'skill_type', 'category__name')
    ordering_fields = ('name', 'sort_order', 'proficiency')
    filter_fields = {'type': 'skill_type', 'category': 'category__slug'}


class PublicSkillCategoryViewSet(QueryParameterFiltersMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = (AllowAny,)
    pagination_class = ContentPagination
    serializer_class = SkillCategoryPublicSerializer
    search_fields = ('name',)
    ordering_fields = ('name', 'sort_order')
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    filter_fields = {}
    queryset = SkillCategory.objects.prefetch_related(
        Prefetch(
            'skills',
            queryset=Skill.objects.filter(
                status=PublishableModel.Status.PUBLISHED
            ).select_related('category'),
        )
    ).filter(skills__status=PublishableModel.Status.PUBLISHED).distinct()


class PublicProjectViewSet(PublicContentViewSet):
    queryset = Project.objects.select_related('cover_media').prefetch_related(
        'skills__category',
        'media_links__media',
    )
    serializer_class = ProjectPublicSerializer
    lookup_field = 'slug'
    search_fields = ('title', 'summary', 'description', 'role')
    ordering_fields = ('title', 'published_at', 'sort_order', 'featured')
    filter_fields = {'featured': 'featured', 'skill': 'skills__pk'}
    boolean_filter_fields = ('featured',)


class PublicExperienceViewSet(PublicContentViewSet):
    queryset = Experience.objects.all()
    serializer_class = ExperiencePublicSerializer
    search_fields = ('role', 'organization', 'location', 'description')
    ordering_fields = ('started_on', 'sort_order', 'organization')
    filter_fields = {'current': 'is_current'}
    boolean_filter_fields = ('current',)


class PublicEducationViewSet(PublicContentViewSet):
    queryset = Education.objects.all()
    serializer_class = EducationPublicSerializer
    search_fields = ('institution', 'degree', 'field_of_study', 'location')
    ordering_fields = ('started_on', 'ended_on', 'sort_order', 'institution')
    filter_fields = {'current': 'is_current'}
    boolean_filter_fields = ('current',)


class PublicServiceViewSet(PublicContentViewSet):
    queryset = Service.objects.all()
    serializer_class = ServicePublicSerializer
    lookup_field = 'slug'
    search_fields = ('title', 'description')
    ordering_fields = ('title', 'sort_order')


class PublicTestimonialViewSet(PublicContentViewSet):
    queryset = Testimonial.objects.select_related('avatar')
    serializer_class = TestimonialPublicSerializer
    search_fields = ('person_name', 'person_title', 'organization', 'quote')
    ordering_fields = ('person_name', 'sort_order', 'featured')
    filter_fields = {'featured': 'featured'}
    boolean_filter_fields = ('featured',)


class PublicBlogPostViewSet(PublicContentViewSet):
    queryset = BlogPost.objects.select_related('cover_media')
    serializer_class = BlogPostPublicSerializer
    lookup_field = 'slug'
    search_fields = ('title', 'excerpt', 'body_markdown')
    ordering_fields = ('title', 'published_at')


class PublicSocialLinkViewSet(PublicContentViewSet):
    queryset = SocialLink.objects.all()
    serializer_class = SocialLinkPublicSerializer
    search_fields = ('platform', 'label')
    ordering_fields = ('platform', 'sort_order')


class PublicResumeViewSet(PublicContentViewSet):
    queryset = Resume.objects.select_related('file')
    serializer_class = ResumePublicSerializer
    search_fields = ('title',)
    ordering_fields = ('published_at', 'title', 'is_current')
    filter_fields = {'current': 'is_current'}
    boolean_filter_fields = ('current',)


class PublicContactThrottle(AnonRateThrottle):
    rate = '5/hour'


class PublicContactView(generics.CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ContactPublicCreateSerializer
    queryset = ContactMessage.objects.none()
    throttle_classes = (PublicContactThrottle,)

    @extend_schema(
        tags=('Public content',),
        summary='Submit a contact message',
        responses={201: ContactSubmissionResponseSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {'detail': 'Your message has been received.'},
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    list=extend_schema(tags=('CMS',)),
    retrieve=extend_schema(tags=('CMS',)),
    create=extend_schema(tags=('CMS',)),
    update=extend_schema(tags=('CMS',)),
    partial_update=extend_schema(tags=('CMS',)),
    destroy=extend_schema(tags=('CMS',)),
)
class CMSContentViewSet(QueryParameterFiltersMixin, viewsets.ModelViewSet):
    permission_classes = (IsAdminUser,)
    pagination_class = ContentPagination
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    ordering_fields = ()
    filter_fields = {'status': 'status'}
    serializer_class = None
    queryset = None

    def perform_create(self, serializer):
        if issubclass(self.queryset.model, PublishableModel):
            serializer.save(created_by=self.request.user, updated_by=self.request.user)
        else:
            serializer.save()

    def perform_update(self, serializer):
        if issubclass(self.queryset.model, PublishableModel):
            serializer.save(updated_by=self.request.user)
        else:
            serializer.save()


class CMSPublishableViewSet(CMSContentViewSet):
    @action(detail=True, methods=('post',))
    @extend_schema(summary='Publish this item', request=None)
    def publish(self, request, *args, **kwargs):
        instance = self.get_object()
        if not isinstance(instance, PublishableModel):
            raise ValidationError('This resource does not support publication.')
        instance.publish()
        instance.updated_by = request.user
        instance.save(update_fields=('status', 'published_at', 'updated_by', 'updated_at'))
        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=('post',))
    @extend_schema(summary='Unpublish this item', request=None)
    def unpublish(self, request, *args, **kwargs):
        instance = self.get_object()
        if not isinstance(instance, PublishableModel):
            raise ValidationError('This resource does not support publication.')
        instance.unpublish()
        instance.updated_by = request.user
        instance.save(update_fields=('status', 'updated_by', 'updated_at'))
        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=('get',))
    @extend_schema(summary='Preview this item without changing publication status')
    def preview(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response(self.get_serializer(instance).data)


class CMSProfileViewSet(CMSPublishableViewSet):
    queryset = Profile.objects.select_related('avatar')
    serializer_class = ProfileCMSSerializer
    search_fields = ('name', 'headline', 'email')
    ordering_fields = ('name', 'created_at')


class CMSCategoryViewSet(CMSContentViewSet):
    queryset = SkillCategory.objects.all()
    serializer_class = SkillCategoryCMSSerializer
    search_fields = ('name', 'slug')
    ordering_fields = ('name', 'sort_order')
    filter_fields = {}


class CMSSkillViewSet(CMSPublishableViewSet):
    queryset = Skill.objects.select_related('category')
    serializer_class = SkillCMSSerializer
    search_fields = ('name', 'skill_type', 'category__name')
    ordering_fields = ('name', 'sort_order', 'proficiency')


class CMSProjectViewSet(CMSPublishableViewSet):
    queryset = Project.objects.select_related('cover_media').prefetch_related(
        'skills',
        'media_links__media',
    )
    serializer_class = ProjectCMSSerializer
    search_fields = ('title', 'summary', 'description', 'role')
    ordering_fields = ('title', 'published_at', 'sort_order', 'featured')
    filter_fields = {'status': 'status', 'featured': 'featured'}
    boolean_filter_fields = ('featured',)


class CMSExperienceViewSet(CMSPublishableViewSet):
    queryset = Experience.objects.all()
    serializer_class = ExperienceCMSSerializer
    search_fields = ('role', 'organization', 'location')
    ordering_fields = ('started_on', 'sort_order', 'organization')


class CMSEducationViewSet(CMSPublishableViewSet):
    queryset = Education.objects.all()
    serializer_class = EducationCMSSerializer
    search_fields = ('institution', 'degree', 'field_of_study')
    ordering_fields = ('started_on', 'ended_on', 'sort_order', 'institution')


class CMSServiceViewSet(CMSPublishableViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceCMSSerializer
    search_fields = ('title', 'description')
    ordering_fields = ('title', 'sort_order')


class CMSTestimonialViewSet(CMSPublishableViewSet):
    queryset = Testimonial.objects.select_related('avatar')
    serializer_class = TestimonialCMSSerializer
    search_fields = ('person_name', 'organization', 'quote')
    ordering_fields = ('person_name', 'sort_order', 'featured')


class CMSBlogPostViewSet(CMSPublishableViewSet):
    queryset = BlogPost.objects.select_related('cover_media')
    serializer_class = BlogPostCMSSerializer
    search_fields = ('title', 'excerpt', 'body_markdown')
    ordering_fields = ('title', 'published_at')


class CMSSocialLinkViewSet(CMSPublishableViewSet):
    queryset = SocialLink.objects.all()
    serializer_class = SocialLinkCMSSerializer
    search_fields = ('platform', 'label', 'url')
    ordering_fields = ('platform', 'sort_order')


class CMSResumeViewSet(CMSPublishableViewSet):
    queryset = Resume.objects.select_related('file')
    serializer_class = ResumeCMSSerializer
    search_fields = ('title',)
    ordering_fields = ('published_at', 'title', 'is_current')


class CMSMediaViewSet(CMSContentViewSet):
    queryset = Media.objects.select_related('uploaded_by')
    serializer_class = MediaCMSSerializer
    search_fields = ('original_filename', 'caption', 'alt_text', 'mime_type')
    ordering_fields = ('created_at', 'original_filename', 'size_bytes')
    filter_fields = {'kind': 'kind'}

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        file_name = instance.file.name if instance.file else None
        try:
            self.perform_destroy(instance)
        except ProtectedError:
            return Response(
                {'detail': 'Media referenced by content cannot be deleted.'},
                status=status.HTTP_409_CONFLICT,
            )
        if file_name:
            instance.file.storage.delete(file_name)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CMSContactViewSet(CMSContentViewSet):
    queryset = ContactMessage.objects.all()
    serializer_class = ContactCMSSerializer
    search_fields = ('name', 'email', 'subject', 'message')
    ordering_fields = ('received_at', 'status', 'name')
    filter_fields = {'status': 'status'}


class CMSProjectMediaViewSet(CMSContentViewSet):
    queryset = ProjectMedia.objects.select_related('project', 'media')
    serializer_class = ProjectMediaCMSSerializer
    search_fields = ('project__title', 'media__original_filename', 'caption')
    ordering_fields = ('position', 'project__title')
    filter_fields = {}
