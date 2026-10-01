from datetime import date, datetime, timezone as datetime_timezone
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from .models import (
    BlogPost,
    ContactMessage,
    Education,
    Experience,
    Media,
    Profile,
    Project,
    PublishableModel,
    Resume,
    Service,
    Skill,
    SkillCategory,
    SocialLink,
    Testimonial,
)


class ContentApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = get_user_model().objects.create_user(
            username='content-admin',
            password='Strong-local-test-password-42',
            is_staff=True,
        )
        self.regular_user = get_user_model().objects.create_user(
            username='content-editor',
            password='Strong-local-test-password-42',
        )

    def publish(self, item, published_at=None):
        item.status = PublishableModel.Status.PUBLISHED
        item.published_at = published_at or timezone.now()
        item.save()
        return item

    def test_public_api_exposes_only_published_content_and_associated_media(self):
        image = Media.objects.create(
            file='content/media/portrait.png',
            kind=Media.Kind.IMAGE,
            original_filename='portrait.png',
            mime_type='image/png',
            size_bytes=12,
            alt_text='Portrait',
        )
        published_profile = self.publish(Profile.objects.create(
            name='Portfolio Owner',
            headline='Engineer',
            avatar=image,
        ))
        category = SkillCategory.objects.create(name='Languages', slug='languages')
        published_skill = self.publish(
            Skill.objects.create(name='Python', category=category)
        )
        draft_skill = Skill.objects.create(name='Draft skill', category=category)
        published_project = Project.objects.create(
            title='Public project',
            slug='public-project',
            summary='Visible project',
            cover_media=image,
        )
        self.publish(published_project)
        published_project.skills.add(published_skill)
        BlogPost.objects.create(
            title='Draft notes',
            slug='draft-notes',
            excerpt='Hidden',
            body_markdown='Hidden body',
        )
        post = BlogPost.objects.create(
            title='Public notes',
            slug='public-notes',
            excerpt='Visible',
            body_markdown='Visible body',
        )
        self.publish(post)

        self.assertEqual(
            self.client.get('/api/public/profile/').data['id'],
            published_profile.pk,
        )
        self.assertEqual(
            self.client.get('/api/public/skills/').data['results'][0]['name'],
            published_skill.name,
        )
        category_response = self.client.get('/api/public/skill-categories/')
        self.assertEqual(len(category_response.data['results']), 1)
        self.assertEqual(
            [skill['name'] for skill in category_response.data['results'][0]['skills']],
            ['Python'],
        )
        project_response = self.client.get('/api/public/projects/public-project/')
        self.assertEqual(project_response.status_code, status.HTTP_200_OK)
        self.assertEqual(project_response.data['cover_media']['original_filename'], 'portrait.png')
        self.assertEqual(project_response.data['skills'][0]['name'], 'Python')
        self.assertEqual(
            self.client.get('/api/public/blog/public-notes/').status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.get('/api/public/blog/draft-notes/').status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.get(f'/api/public/skills/{draft_skill.pk}/').status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(self.client.get('/api/public/media/').status_code, 404)

    @override_settings(
        DEBUG=True,
        ROOT_URLCONF='content.test_media_urls',
    )
    def test_uploaded_media_is_served_in_development_and_can_be_deleted(self):
        image_content = (
            b'\x89PNG\r\n\x1a\n'
            b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
        )
        self.client.force_authenticate(user=self.staff)
        upload_response = self.client.post(
            '/api/cms/media/',
            {
                'kind': Media.Kind.IMAGE,
                'upload': SimpleUploadedFile(
                    'portrait.png',
                    image_content,
                    content_type='image/png',
                ),
            },
            format='multipart',
        )
        self.assertEqual(upload_response.status_code, status.HTTP_201_CREATED)
        media_url = upload_response.data['file_url']
        media = Media.objects.get(pk=upload_response.data['id'])
        file_name = media.file.name
        self.assertTrue(default_storage.exists(file_name))

        try:
            file_response = self.client.get(media_url)
            self.assertEqual(file_response.status_code, status.HTTP_200_OK)
            try:
                self.assertEqual(b''.join(file_response.streaming_content), image_content)
            finally:
                if not file_response.closed:
                    file_response.close()

            delete_response = self.client.delete(
                f"/api/cms/media/{upload_response.data['id']}/"
            )
            self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertEqual(self.client.get(media_url).status_code, status.HTTP_404_NOT_FOUND)
        finally:
            default_storage.delete(file_name)
            Media.objects.filter(pk=media.pk).delete()

    def test_public_lists_are_paginated_filterable_and_searchable(self):
        self.publish(Project.objects.create(
            title='Featured build',
            slug='featured-build',
            summary='A visible build',
            featured=True,
        ))
        self.publish(Project.objects.create(
            title='Other build',
            slug='other-build',
            summary='Another visible build',
        ))
        response = self.client.get('/api/public/projects/?featured=true&page_size=1')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertTrue(response.data['results'][0]['featured'])
        invalid_filter = self.client.get('/api/public/projects/?featured=yes')
        self.assertEqual(invalid_filter.status_code, status.HTTP_400_BAD_REQUEST)

    def test_published_categories_with_no_published_skills_are_hidden(self):
        SkillCategory.objects.create(name='Empty', slug='empty')
        self.assertEqual(
            self.client.get('/api/public/skill-categories/').data['count'],
            0,
        )

    def test_public_apis_cover_experience_education_services_testimonials_social_and_resume(self):
        document = Media.objects.create(
            file='content/media/resume.pdf',
            kind=Media.Kind.DOCUMENT,
            original_filename='resume.pdf',
            mime_type='application/pdf',
            size_bytes=12,
        )
        records = (
            (
                Experience.objects.create(
                    role='Engineer',
                    organization='Example Co',
                    started_on=date(2024, 1, 1),
                ),
                '/api/public/experience/',
            ),
            (
                Education.objects.create(
                    institution='Example University',
                    degree='BSc',
                ),
                '/api/public/education/',
            ),
            (
                Service.objects.create(
                    title='Consulting',
                    slug='consulting',
                    description='Technical consulting',
                ),
                '/api/public/services/',
            ),
            (
                Testimonial.objects.create(
                    person_name='Jamie Example',
                    quote='Excellent work on the project.',
                ),
                '/api/public/testimonials/',
            ),
            (
                SocialLink.objects.create(
                    platform='GitHub',
                    label='GitHub profile',
                    url='https://example.com/jamie',
                ),
                '/api/public/social-links/',
            ),
            (
                Resume.objects.create(title='Current resume', file=document, is_current=True),
                '/api/public/resume/',
            ),
        )
        for record, endpoint in records:
            self.publish(record)
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['count'], 1, endpoint)

    def test_public_contact_submission_validates_and_creates_new_message(self):
        response = self.client.post(
            '/api/public/contact/',
            {
                'name': 'Jamie Example',
                'email': 'jamie@example.com',
                'subject': 'Hello',
                'message': 'Please get in touch.',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ContactMessage.objects.get().status, ContactMessage.Status.NEW)
        self.assertNotIn('status', response.data)
        self.assertNotIn('email', response.data)
        invalid = self.client.post(
            '/api/public/contact/',
            {'name': 'J', 'email': 'bad-email', 'message': 'short'},
            format='json',
        )
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ContactMessage.objects.count(), 1)

    def test_cms_requires_an_is_admin_user(self):
        anonymous = self.client.get('/api/cms/projects/')
        self.assertEqual(anonymous.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(self.regular_user)
        forbidden = self.client.get('/api/cms/projects/')
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.staff)
        allowed = self.client.get('/api/cms/projects/')
        self.assertEqual(allowed.status_code, status.HTTP_200_OK)

    def test_cms_publish_unpublish_and_preview_preserve_publication_semantics(self):
        self.client.force_authenticate(self.staff)
        project = Project.objects.create(
            title='Lifecycle project',
            slug='lifecycle-project',
            summary='Lifecycle',
        )
        first_publication = datetime(2026, 2, 1, tzinfo=datetime_timezone.utc)
        with patch('content.models.timezone.now', return_value=first_publication):
            preview = self.client.get(f'/api/cms/projects/{project.pk}/preview/')
        self.assertEqual(preview.status_code, status.HTTP_200_OK)
        self.assertEqual(preview.data['status'], 'draft')
        project.refresh_from_db()
        self.assertEqual(project.status, PublishableModel.Status.DRAFT)
        self.assertIsNone(project.published_at)
        self.assertEqual(
            self.client.get('/api/public/projects/lifecycle-project/').status_code,
            status.HTTP_404_NOT_FOUND,
        )

        with patch('content.models.timezone.now', return_value=first_publication):
            published = self.client.post(f'/api/cms/projects/{project.pk}/publish/')
        self.assertEqual(published.status_code, status.HTTP_200_OK)
        self.assertEqual(published.data['status'], 'published')
        self.assertEqual(
            project.__class__.objects.get(pk=project.pk).published_at,
            first_publication,
        )

        updated = self.client.patch(
            f'/api/cms/projects/{project.pk}/',
            {'summary': 'Updated while published'},
            format='json',
        )
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        self.assertEqual(updated.data['published_at'], '2026-02-01T00:00:00Z')

        unpublished = self.client.post(f'/api/cms/projects/{project.pk}/unpublish/')
        self.assertEqual(unpublished.data['status'], 'draft')
        self.assertEqual(unpublished.data['published_at'], '2026-02-01T00:00:00Z')
        self.assertEqual(
            self.client.get('/api/public/projects/lifecycle-project/').status_code,
            status.HTTP_404_NOT_FOUND,
        )

        second_publication = datetime(2026, 3, 1, tzinfo=datetime_timezone.utc)
        with patch('content.models.timezone.now', return_value=second_publication):
            republished = self.client.post(f'/api/cms/projects/{project.pk}/publish/')
        self.assertEqual(republished.data['published_at'], '2026-03-01T00:00:00Z')

    def test_cms_rejects_invalid_model_constraints(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            '/api/cms/experience/',
            {
                'role': 'Developer',
                'organization': 'Example Co',
                'started_on': date(2025, 5, 1).isoformat(),
                'ended_on': date(2025, 4, 1).isoformat(),
                'is_current': False,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('ended_on', response.data)
        self.assertEqual(Experience.objects.count(), 0)

    def test_cms_manages_contact_status_and_categories(self):
        self.client.force_authenticate(self.staff)
        message = ContactMessage.objects.create(
            name='Taylor Example',
            email='taylor@example.com',
            message='A contact request with sufficient detail.',
        )
        updated = self.client.patch(
            f'/api/cms/contacts/{message.pk}/',
            {'status': ContactMessage.Status.READ},
            format='json',
        )
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        self.assertEqual(updated.data['status'], ContactMessage.Status.READ)
        message.refresh_from_db()
        self.assertIsNotNone(message.read_at)
        replied = self.client.patch(
            f'/api/cms/contacts/{message.pk}/',
            {'status': ContactMessage.Status.REPLIED},
            format='json',
        )
        self.assertEqual(replied.status_code, status.HTTP_200_OK)
        message.refresh_from_db()
        self.assertIsNotNone(message.replied_at)
        self.assertIsNotNone(message.read_at)

        category = self.client.post(
            '/api/cms/skill-categories/',
            {'name': 'Frameworks', 'slug': 'frameworks'},
            format='json',
        )
        self.assertEqual(category.status_code, status.HTTP_201_CREATED)
        self.assertEqual(category.data['name'], 'Frameworks')
        self.assertNotIn('publish', category.data)

    def test_cms_crud_serializers_cover_remaining_content_resources(self):
        self.client.force_authenticate(self.staff)
        document = Media.objects.create(
            file='content/media/cms-resume.pdf',
            kind=Media.Kind.DOCUMENT,
            original_filename='cms-resume.pdf',
            mime_type='application/pdf',
            size_bytes=12,
        )
        cases = (
            (
                '/api/cms/skills/',
                {'name': 'Python', 'skill_type': 'technical'},
            ),
            (
                '/api/cms/education/',
                {'institution': 'Example University', 'degree': 'BSc'},
            ),
            (
                '/api/cms/services/',
                {
                    'title': 'Consulting',
                    'slug': 'cms-consulting',
                    'description': 'Technical consulting',
                },
            ),
            (
                '/api/cms/testimonials/',
                {'person_name': 'Jamie Example', 'quote': 'Excellent work.'},
            ),
            (
                '/api/cms/blog/',
                {
                    'title': 'CMS notes',
                    'slug': 'cms-notes',
                    'excerpt': 'A brief note.',
                    'body_markdown': 'Long-form content.',
                },
            ),
            (
                '/api/cms/social-links/',
                {
                    'platform': 'GitHub',
                    'label': 'GitHub profile',
                    'url': 'https://example.com/cms',
                },
            ),
            (
                '/api/cms/resume/',
                {'title': 'CMS resume', 'file': document.pk},
            ),
            (
                '/api/cms/profiles/',
                {'name': 'Portfolio Owner', 'headline': 'Engineer'},
            ),
        )
        for endpoint, payload in cases:
            with self.subTest(endpoint=endpoint):
                response = self.client.post(endpoint, payload, format='json')
                self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
                self.assertEqual(response.data['status'], PublishableModel.Status.DRAFT)

    def test_cms_project_gallery_supports_safe_reordering(self):
        self.client.force_authenticate(self.staff)
        first = Media.objects.create(
            file='content/media/first.png',
            kind=Media.Kind.IMAGE,
            original_filename='first.png',
            mime_type='image/png',
            size_bytes=10,
        )
        second = Media.objects.create(
            file='content/media/second.png',
            kind=Media.Kind.IMAGE,
            original_filename='second.png',
            mime_type='image/png',
            size_bytes=10,
        )
        project = Project.objects.create(
            title='Gallery project',
            slug='gallery-project',
            summary='A project with gallery items',
        )
        project.media_links.create(media=first, position=0)
        project.media_links.create(media=second, position=1)

        response = self.client.patch(
            f'/api/cms/projects/{project.pk}/',
            {'gallery_media_ids': [second.pk, first.pk]},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(
            [item['media']['id'] for item in response.data['gallery_media']],
            [second.pk, first.pk],
        )
        self.assertEqual(
            list(project.media_links.order_by('position').values_list('media_id', flat=True)),
            [second.pk, first.pk],
        )

    def test_cms_media_upload_is_staff_only_and_validates_kind(self):
        self.client.force_authenticate(self.staff)
        bad_upload = self.client.post(
            '/api/cms/media/',
            {
                'kind': Media.Kind.IMAGE,
                'upload': SimpleUploadedFile(
                    'resume.pdf',
                    b'not-an-image',
                    content_type='application/pdf',
                ),
            },
            format='multipart',
        )
        self.assertEqual(bad_upload.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Media.objects.count(), 0)

    def test_cms_media_upload_records_server_derived_metadata(self):
        self.client.force_authenticate(self.staff)
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            response = self.client.post(
                '/api/cms/media/',
                {
                    'kind': Media.Kind.IMAGE,
                    'upload': SimpleUploadedFile(
                        'profile.png',
                        b'\x89PNG\r\n\x1a\nvalid-png-payload',
                        content_type='image/png',
                    ),
                    'alt_text': 'Profile photo',
                },
                format='multipart',
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        media = Media.objects.get()
        self.assertEqual(media.original_filename, 'profile.png')
        self.assertEqual(media.mime_type, 'image/png')
        self.assertEqual(media.size_bytes, len(b'\x89PNG\r\n\x1a\nvalid-png-payload'))
        self.assertEqual(media.uploaded_by, self.staff)

    def test_cms_media_upload_validates_signature_type_extension_and_size(self):
        self.client.force_authenticate(self.staff)
        accepted_files = (
            ('portrait.png', b'\x89PNG\r\n\x1a\npayload', 'image/png', Media.Kind.IMAGE),
            ('portrait.jpg', b'\xff\xd8\xffpayload', 'image/jpeg', Media.Kind.IMAGE),
            ('portrait.gif', b'GIF89apayload', 'image/gif', Media.Kind.IMAGE),
            ('portrait.webp', b'RIFF\x00\x00\x00\x00WEBPpayload', 'image/webp', Media.Kind.IMAGE),
            ('resume.pdf', b'%PDF-1.7\npayload', 'application/pdf', Media.Kind.DOCUMENT),
        )
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            for filename, contents, expected_type, kind in accepted_files:
                with self.subTest(filename=filename):
                    response = self.client.post(
                        '/api/cms/media/',
                        {
                            'kind': kind,
                            'upload': SimpleUploadedFile(
                                filename,
                                contents,
                                content_type='application/octet-stream',
                            ),
                        },
                        format='multipart',
                    )

                    self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
                    self.assertEqual(response.data['mime_type'], expected_type)

            rejected_files = (
                ('spoofed.png', b'<html>not an image</html>', 'image/png', Media.Kind.IMAGE),
                ('mismatched.jpg', b'\x89PNG\r\n\x1a\npayload', 'image/png', Media.Kind.IMAGE),
                ('wrong-kind.pdf', b'%PDF-1.7\npayload', 'application/pdf', Media.Kind.IMAGE),
                (
                    'oversized.png',
                    b'\x89PNG\r\n\x1a\n' + b'x' * (10 * 1024 * 1024 + 1),
                    'image/png',
                    Media.Kind.IMAGE,
                ),
            )
            for filename, contents, content_type, kind in rejected_files:
                with self.subTest(filename=filename):
                    response = self.client.post(
                        '/api/cms/media/',
                        {
                            'kind': kind,
                            'upload': SimpleUploadedFile(
                                filename,
                                contents,
                                content_type=content_type,
                            ),
                        },
                        format='multipart',
                    )

                    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cms_media_type_cannot_change_without_reupload(self):
        self.client.force_authenticate(self.staff)
        document = Media.objects.create(
            file='content/media/resume.pdf',
            kind=Media.Kind.DOCUMENT,
            original_filename='resume.pdf',
            mime_type='application/pdf',
            size_bytes=12,
        )

        response = self.client.patch(
            f'/api/cms/media/{document.pk}/',
            {'kind': Media.Kind.IMAGE},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        document.refresh_from_db()
        self.assertEqual(document.kind, Media.Kind.DOCUMENT)

    def test_cms_media_cannot_delete_assets_referenced_by_content(self):
        self.client.force_authenticate(self.staff)
        image = Media.objects.create(
            file='content/media/referenced.png',
            kind=Media.Kind.IMAGE,
            original_filename='referenced.png',
            mime_type='image/png',
            size_bytes=10,
        )
        Profile.objects.create(
            name='Portfolio Owner',
            headline='Engineer',
            avatar=image,
        )

        response = self.client.delete(f'/api/cms/media/{image.pk}/')

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(Media.objects.filter(pk=image.pk).exists())

    def test_media_and_public_related_objects_are_query_optimized(self):
        image = Media.objects.create(
            file='content/media/project.png',
            kind=Media.Kind.IMAGE,
            original_filename='project.png',
            mime_type='image/png',
            size_bytes=10,
        )
        project = Project.objects.create(
            title='Query project',
            slug='query-project',
            summary='Testing eager loading',
            cover_media=image,
        )
        self.publish(project)
        with self.assertNumQueries(4):
            response = self.client.get('/api/public/projects/')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            response.data['results'][0]['cover_media']['file_url']
