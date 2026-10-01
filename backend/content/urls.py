from rest_framework.routers import DefaultRouter
from django.urls import include, path

from .views import (
    CMSBlogPostViewSet,
    CMSCategoryViewSet,
    CMSContactViewSet,
    CMSEducationViewSet,
    CMSExperienceViewSet,
    CMSMediaViewSet,
    CMSProfileViewSet,
    CMSProjectMediaViewSet,
    CMSProjectViewSet,
    CMSResumeViewSet,
    CMSServiceViewSet,
    CMSSkillViewSet,
    CMSSocialLinkViewSet,
    CMSTestimonialViewSet,
    ProfilePublicView,
    PublicBlogPostViewSet,
    PublicContactView,
    PublicEducationViewSet,
    PublicExperienceViewSet,
    PublicProjectViewSet,
    PublicResumeViewSet,
    PublicServiceViewSet,
    PublicSkillCategoryViewSet,
    PublicSkillViewSet,
    PublicSocialLinkViewSet,
    PublicTestimonialViewSet,
)


public_router = DefaultRouter()
public_router.register('skills', PublicSkillViewSet, basename='public-skill')
public_router.register(
    'skill-categories',
    PublicSkillCategoryViewSet,
    basename='public-skill-category',
)
public_router.register('projects', PublicProjectViewSet, basename='public-project')
public_router.register(
    'experience',
    PublicExperienceViewSet,
    basename='public-experience',
)
public_router.register('education', PublicEducationViewSet, basename='public-education')
public_router.register('services', PublicServiceViewSet, basename='public-service')
public_router.register(
    'testimonials',
    PublicTestimonialViewSet,
    basename='public-testimonial',
)
public_router.register('blog', PublicBlogPostViewSet, basename='public-blog')
public_router.register('social-links', PublicSocialLinkViewSet, basename='public-social-link')
public_router.register('resume', PublicResumeViewSet, basename='public-resume')

cms_router = DefaultRouter()
cms_router.register('profiles', CMSProfileViewSet, basename='cms-profile')
cms_router.register('skill-categories', CMSCategoryViewSet, basename='cms-skill-category')
cms_router.register('skills', CMSSkillViewSet, basename='cms-skill')
cms_router.register('projects', CMSProjectViewSet, basename='cms-project')
cms_router.register('experience', CMSExperienceViewSet, basename='cms-experience')
cms_router.register('education', CMSEducationViewSet, basename='cms-education')
cms_router.register('services', CMSServiceViewSet, basename='cms-service')
cms_router.register('testimonials', CMSTestimonialViewSet, basename='cms-testimonial')
cms_router.register('blog', CMSBlogPostViewSet, basename='cms-blog')
cms_router.register('social-links', CMSSocialLinkViewSet, basename='cms-social-link')
cms_router.register('resume', CMSResumeViewSet, basename='cms-resume')
cms_router.register('media', CMSMediaViewSet, basename='cms-media')
cms_router.register('contacts', CMSContactViewSet, basename='cms-contact')
cms_router.register(
    'project-media',
    CMSProjectMediaViewSet,
    basename='cms-project-media',
)

urlpatterns = [
    path('public/profile/', ProfilePublicView.as_view(), name='public-profile'),
    path('public/contact/', PublicContactView.as_view(), name='public-contact'),
    path('public/', include(public_router.urls)),
    path('cms/', include(cms_router.urls)),
]
