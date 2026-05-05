from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from projects.models import Project, ProjectMember
from .helpers import (
    make_user, make_org, add_org_member, make_project,
    add_project_member, get_access_token,
)


class ProjectListTest(APITestCase):
    def setUp(self):
        self.user = make_user(1)
        self.other = make_user(2)
        self.org = make_org()
        add_org_member(self.org, self.user, 'owner')
        add_org_member(self.org, self.other, 'member')

        self.my_project = make_project(self.org, owner=self.user, key='MY')
        add_project_member(self.my_project, self.user, 'owner')

        self.other_project = make_project(self.org, owner=self.other, key='OT')
        add_project_member(self.other_project, self.other, 'owner')

        access, _ = get_access_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        self.url = reverse('api_project_list')

    def test_returns_only_my_projects(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [p['id'] for p in response.data['results']]
        self.assertIn(str(self.my_project.id), ids)
        self.assertNotIn(str(self.other_project.id), ids)

    def test_unauthenticated_returns_401(self):
        self.client.credentials()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_soft_deleted_project_excluded(self):
        self.my_project.soft_delete()
        response = self.client.get(self.url)
        ids = [p['id'] for p in response.data['results']]
        self.assertNotIn(str(self.my_project.id), ids)


class ProjectDetailTest(APITestCase):
    def setUp(self):
        self.user = make_user(1)
        self.org = make_org()
        add_org_member(self.org, self.user, 'owner')
        self.project = make_project(self.org, owner=self.user, key='PR')
        add_project_member(self.project, self.user, 'owner')

        access, _ = get_access_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        self.url = reverse('api_project_detail', kwargs={'pk': self.project.pk})

    def test_member_can_retrieve_project(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.project.name)

    def test_non_member_gets_404(self):
        outsider = make_user(2)
        access, _ = get_access_token(outsider)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_response_includes_user_role(self):
        response = self.client.get(self.url)
        self.assertEqual(response.data['role'], 'owner')


class ProjectUpdateTest(APITestCase):
    def setUp(self):
        self.org = make_org()

        self.owner = make_user(1)
        self.manager = make_user(2)
        self.developer = make_user(3)
        self.viewer = make_user(4)

        for u in [self.owner, self.manager, self.developer, self.viewer]:
            add_org_member(self.org, u, 'member')

        self.project = make_project(self.org, owner=self.owner, key='PR')
        add_project_member(self.project, self.owner, 'owner')
        add_project_member(self.project, self.manager, 'manager')
        add_project_member(self.project, self.developer, 'developer')
        add_project_member(self.project, self.viewer, 'viewer')

        self.url = reverse('api_project_detail', kwargs={'pk': self.project.pk})

    def _auth(self, user):
        access, _ = get_access_token(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

    def test_owner_can_update_project(self):
        self._auth(self.owner)
        response = self.client.patch(self.url, {'name': 'Updated Name'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_manager_can_update_project(self):
        self._auth(self.manager)
        response = self.client.patch(self.url, {'name': 'Manager Update'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_developer_cannot_update_project(self):
        self._auth(self.developer)
        response = self.client.patch(self.url, {'name': 'Dev Hack'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_viewer_cannot_update_project(self):
        self._auth(self.viewer)
        response = self.client.patch(self.url, {'name': 'Viewer Hack'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
