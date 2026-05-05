from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from tasks.models import Comment
from .helpers import (
    make_user, make_org, add_org_member, make_project,
    add_project_member, make_task, get_access_token,
)


class CommentListTest(APITestCase):
    def setUp(self):
        self.user = make_user(1)
        self.other = make_user(2)
        self.org = make_org()
        add_org_member(self.org, self.user, 'member')
        add_org_member(self.org, self.other, 'member')
        self.project = make_project(self.org, key='CL')
        add_project_member(self.project, self.user, 'developer')
        add_project_member(self.project, self.other, 'developer')
        self.task = make_task(self.project)

        Comment.objects.create(task=self.task, user=self.user, content='Visible')
        deleted = Comment.objects.create(task=self.task, user=self.other, content='Deleted')
        from django.utils import timezone
        deleted.deleted_at = timezone.now()
        deleted.save()

        access, _ = get_access_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        self.url = reverse('api_comment_list', kwargs={
            'project_pk': self.project.pk, 'task_pk': self.task.pk
        })

    def test_only_active_comments_returned(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        contents = [c['content'] for c in response.data['results']]
        self.assertIn('Visible', contents)
        self.assertNotIn('Deleted', contents)

    def test_non_member_gets_404(self):
        outsider = make_user(3)
        access, _ = get_access_token(outsider)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CommentCreateTest(APITestCase):
    def setUp(self):
        self.user = make_user(1)
        self.org = make_org()
        add_org_member(self.org, self.user, 'member')
        self.project = make_project(self.org, key='CC')
        add_project_member(self.project, self.user, 'developer')
        self.task = make_task(self.project)

        access, _ = get_access_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        self.url = reverse('api_comment_list', kwargs={
            'project_pk': self.project.pk, 'task_pk': self.task.pk
        })

    def test_member_can_create_comment(self):
        response = self.client.post(self.url, {'content': 'My comment'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Comment.objects.filter(content='My comment', user=self.user).exists())

    def test_author_is_set_to_current_user(self):
        self.client.post(self.url, {'content': 'Auth check'})
        comment = Comment.objects.get(content='Auth check')
        self.assertEqual(comment.user, self.user)

    def test_empty_content_rejected(self):
        response = self.client.post(self.url, {'content': ''})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CommentDeleteTest(APITestCase):
    def setUp(self):
        self.author = make_user(1)
        self.other_user = make_user(2)
        self.org = make_org()
        add_org_member(self.org, self.author, 'member')
        add_org_member(self.org, self.other_user, 'member')
        self.project = make_project(self.org, key='CD')
        add_project_member(self.project, self.author, 'developer')
        add_project_member(self.project, self.other_user, 'developer')
        self.task = make_task(self.project)
        self.comment = Comment.objects.create(
            task=self.task, user=self.author, content='Delete me'
        )

    def _url(self):
        return reverse('api_comment_destroy', kwargs={
            'project_pk': self.project.pk,
            'task_pk': self.task.pk,
            'pk': self.comment.pk,
        })

    def _auth(self, user):
        access, _ = get_access_token(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

    def test_author_can_soft_delete_own_comment(self):
        self._auth(self.author)
        response = self.client.delete(self._url())
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.comment.refresh_from_db()
        self.assertIsNotNone(self.comment.deleted_at)

    def test_other_user_cannot_delete_comment(self):
        self._auth(self.other_user)
        response = self.client.delete(self._url())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.comment.refresh_from_db()
        self.assertIsNone(self.comment.deleted_at)

    def test_unauthenticated_cannot_delete(self):
        response = self.client.delete(self._url())
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
