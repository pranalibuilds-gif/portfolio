from datetime import datetime, timezone as datetime_timezone
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import (
    BlogPost,
    Media,
    Profile,
    PublishableModel,
    Resume,
    Skill,
    SkillCategory,
)


class PublishableContentTests(TestCase):
    def create_post(self):
        return BlogPost.objects.create(
            title='Design notes',
            slug='design-notes',
            excerpt='A short summary',
            body_markdown='Post body',
        )

    def test_publish_and_republish_update_latest_publication_timestamp(self):
        first_publication = datetime(2026, 1, 1, tzinfo=datetime_timezone.utc)
        second_publication = datetime(2026, 2, 1, tzinfo=datetime_timezone.utc)
        post = self.create_post()

        with patch('content.models.timezone.now', return_value=first_publication):
            post.publish()
        post.save()
        self.assertEqual(post.status, PublishableModel.Status.PUBLISHED)
        self.assertEqual(post.published_at, first_publication)

        post.unpublish()
        post.save()
        self.assertEqual(post.status, PublishableModel.Status.DRAFT)
        self.assertEqual(post.published_at, first_publication)

        with patch('content.models.timezone.now', return_value=second_publication):
            post.publish()
        post.save()
        self.assertEqual(post.published_at, second_publication)

    def test_draft_edits_do_not_change_last_publication_timestamp(self):
        post = self.create_post()
        post.published_at = datetime(2026, 1, 1, tzinfo=datetime_timezone.utc)
        post.save(update_fields=['published_at'])

        post.title = 'Draft update'
        post.save(update_fields=['title'])
        post.refresh_from_db()

        self.assertEqual(
            post.published_at,
            datetime(2026, 1, 1, tzinfo=datetime_timezone.utc),
        )

    def test_publishing_requires_publication_timestamp(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                BlogPost.objects.create(
                    title='Invalid publication',
                    slug='invalid-publication',
                    excerpt='Missing publication time',
                    body_markdown='Body',
                    status=PublishableModel.Status.PUBLISHED,
                )


class DomainConstraintTests(TestCase):
    def test_profile_singleton_constraint_allows_only_one_profile(self):
        Profile.objects.create(name='Portfolio Owner', headline='Developer')

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Profile.objects.create(name='Second Profile', headline='Designer')

    def test_skill_category_is_structural_and_skills_are_independently_published(self):
        category = SkillCategory.objects.create(name='Languages', slug='languages')
        published_skill = Skill.objects.create(
            name='Python',
            category=category,
            status=PublishableModel.Status.PUBLISHED,
            published_at=datetime(2026, 1, 1, tzinfo=datetime_timezone.utc),
        )
        draft_skill = Skill.objects.create(
            name='Rust',
            category=category,
        )

        self.assertFalse(hasattr(category, 'status'))
        self.assertEqual(
            list(category.skills.filter(status=PublishableModel.Status.PUBLISHED)),
            [published_skill],
        )
        self.assertEqual(draft_skill.status, PublishableModel.Status.DRAFT)

    def test_resume_requires_document_media(self):
        image = Media.objects.create(
            file='content/media/image.png',
            kind=Media.Kind.IMAGE,
            original_filename='image.png',
            mime_type='image/png',
            size_bytes=10,
        )
        resume = Resume(title='Resume', file=image)

        with self.assertRaises(ValidationError):
            resume.full_clean()
