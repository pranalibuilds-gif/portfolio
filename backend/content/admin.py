from django.contrib import admin
from .models import (
    BlogPost,
    ContactMessage,
    Education,
    Experience,
    Media,
    Profile,
    Project,
    ProjectMedia,
    Resume,
    Service,
    Skill,
    SkillCategory,
    SocialLink,
    Testimonial,
)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'headline', 'status', 'published_at')
    list_filter = ('status',)
    search_fields = ('name', 'headline', 'email')


@admin.register(SkillCategory)
class SkillCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'sort_order')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'skill_type', 'category', 'status', 'sort_order')
    list_filter = ('status', 'skill_type', 'category')
    search_fields = ('name',)


class ProjectMediaInline(admin.TabularInline):
    model = ProjectMedia
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'featured', 'status', 'published_at')
    list_filter = ('status', 'featured')
    search_fields = ('title', 'summary')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('skills',)
    inlines = (ProjectMediaInline,)


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ('role', 'organization', 'is_current', 'status', 'started_on')
    list_filter = ('status', 'is_current', 'employment_type')
    search_fields = ('role', 'organization')


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ('degree', 'institution', 'is_current', 'status')
    list_filter = ('status', 'is_current')
    search_fields = ('degree', 'institution', 'field_of_study')


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'status', 'sort_order')
    list_filter = ('status',)
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('person_name', 'organization', 'featured', 'status')
    list_filter = ('status', 'featured')
    search_fields = ('person_name', 'organization', 'quote')


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'status', 'published_at')
    list_filter = ('status',)
    search_fields = ('title', 'excerpt', 'body_markdown')
    prepopulated_fields = {'slug': ('title',)}


@admin.register(SocialLink)
class SocialLinkAdmin(admin.ModelAdmin):
    list_display = ('platform', 'label', 'url', 'status', 'sort_order')
    list_filter = ('status', 'platform')
    search_fields = ('platform', 'label', 'url')


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ('title', 'file', 'is_current', 'status', 'published_at')
    list_filter = ('status', 'is_current')
    search_fields = ('title',)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'status', 'received_at')
    list_filter = ('status', 'received_at')
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('received_at', 'created_at', 'updated_at')


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'kind', 'mime_type', 'size_bytes', 'created_at')
    list_filter = ('kind', 'mime_type')
    search_fields = ('original_filename', 'caption', 'alt_text', 'checksum')
    readonly_fields = ('created_at', 'updated_at')
