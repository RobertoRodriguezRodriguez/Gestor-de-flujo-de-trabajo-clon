from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from tasks.models import Task
from .helpers import (
    make_user, make_org, add_org_member, make_project,
    add_project_member, make_task, get_access_token,
)


class TaskListTest(APITestCase):
    def setUp(self):
        self.user = make_user(1)
        self.org = make_org()
        add_org_member(self.org, self.user, 'member')
        self.project = make_project(self.org, key='TL')
        add_project_member(self.project, self.user, 'developer')

        self.task1 = make_task(self.project, title='Task 1', status='todo')
        self.task2 = make_task(self.project, title='Task 2', status='done')

        access, _ = get_access_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        self.url = reverse('api_task_list', kwargs={'project_pk': self.project.pk})

    def test_lists_all_tasks(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_filter_by_status(self):
        response = self.client.get(self.url + '?status=done')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['status'], 'done')

    def test_non_member_gets_404(self):
        outsider = make_user(2)
        access, _ = get_access_token(outsider)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_returns_401(self):
        self.client.credentials()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TaskCreateTest(APITestCase):
    def setUp(self):
        self.org = make_org()

        self.developer = make_user(1)
        self.viewer = make_user(2)

        add_org_member(self.org, self.developer, 'member')
        add_org_member(self.org, self.viewer, 'member')

        self.project = make_project(self.org, key='TC')
        add_project_member(self.project, self.developer, 'developer')
        add_project_member(self.project, self.viewer, 'viewer')

        self.url = reverse('api_task_list', kwargs={'project_pk': self.project.pk})

    def _auth(self, user):
        access, _ = get_access_token(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

    def test_developer_can_create_task(self):
        self._auth(self.developer)
        response = self.client.post(self.url, {'title': 'New Task', 'type': 'task'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Task.objects.filter(title='New Task').exists())

    def test_viewer_cannot_create_task(self):
        self._auth(self.viewer)
        response = self.client.post(self.url, {'title': 'Hack Task', 'type': 'task'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Task.objects.filter(title='Hack Task').exists())

    def test_create_assigns_project_sequence(self):
        self._auth(self.developer)
        response = self.client.post(self.url, {'title': 'Seq Task', 'type': 'task'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertGreater(response.data['project_sequence'], 0)


class TaskRetrieveTest(APITestCase):
    def setUp(self):
        self.user = make_user(1)
        self.org = make_org()
        add_org_member(self.org, self.user, 'member')
        self.project = make_project(self.org, key='TR')
        add_project_member(self.project, self.user, 'developer')
        self.task = make_task(self.project, title='Retrieve Me')

        access, _ = get_access_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        self.url = reverse('api_task_detail', kwargs={
            'project_pk': self.project.pk, 'pk': self.task.pk
        })

    def test_member_can_retrieve_task(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Retrieve Me')


class TaskUpdateTest(APITestCase):
    def setUp(self):
        self.org = make_org()
        self.developer = make_user(1)
        self.viewer = make_user(2)

        add_org_member(self.org, self.developer, 'member')
        add_org_member(self.org, self.viewer, 'member')

        self.project = make_project(self.org, key='TU')
        add_project_member(self.project, self.developer, 'developer')
        add_project_member(self.project, self.viewer, 'viewer')
        self.task = make_task(self.project)

    def _url(self):
        return reverse('api_task_detail', kwargs={
            'project_pk': self.project.pk, 'pk': self.task.pk
        })

    def _auth(self, user):
        access, _ = get_access_token(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

    def test_developer_can_update_task(self):
        self._auth(self.developer)
        response = self.client.patch(self._url(), {'title': 'Updated'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, 'Updated')

    def test_viewer_cannot_update_task(self):
        self._auth(self.viewer)
        response = self.client.patch(self._url(), {'title': 'Hacked'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, 'Test Task')


class TaskDeleteTest(APITestCase):
    def setUp(self):
        self.org = make_org()
        self.developer = make_user(1)
        self.viewer = make_user(2)

        add_org_member(self.org, self.developer, 'member')
        add_org_member(self.org, self.viewer, 'member')

        self.project = make_project(self.org, key='TD')
        add_project_member(self.project, self.developer, 'developer')
        add_project_member(self.project, self.viewer, 'viewer')

    def _make_task(self):
        return make_task(self.project)

    def _url(self, task):
        return reverse('api_task_detail', kwargs={
            'project_pk': self.project.pk, 'pk': task.pk
        })

    def _auth(self, user):
        access, _ = get_access_token(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

    def test_developer_can_delete_task(self):
        task = self._make_task()
        self._auth(self.developer)
        response = self.client.delete(self._url(task))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Task.objects.filter(pk=task.pk).exists())

    def test_viewer_cannot_delete_task(self):
        task = self._make_task()
        self._auth(self.viewer)
        response = self.client.delete(self._url(task))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Task.objects.filter(pk=task.pk).exists())
