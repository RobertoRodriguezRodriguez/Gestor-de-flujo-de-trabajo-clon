from django.test import TestCase

from accounts.models import User
from organizations.models import Organization, OrganizationUser
from projects.models import Project, ProjectMember
from projects.permissions import (
    can_view_project,
    can_edit_project,
    can_delete_project,
    can_manage_members,
    can_manage_sprints,
    can_create_task,
    can_edit_task,
    can_delete_task,
    can_manage_tags,
    can_update_task_status,
    can_log_time,
    can_upload_attachment,
)


def make_user(n=1):
    return User.objects.create_user(
        email=f'user{n}@example.com', name=f'User {n}', password='pass'
    )


def make_project():
    org = Organization.objects.create(name='Test Org')
    return Project.objects.create(organization=org, name='Test Project', key='TP')


def make_membership(project, user, role):
    return ProjectMember.objects.create(project=project, user=user, role=role)


class ProjectPermissionBaseTest(TestCase):
    def setUp(self):
        self.project = make_project()
        self.owner_user = make_user(1)
        self.manager_user = make_user(2)
        self.developer_user = make_user(3)
        self.viewer_user = make_user(4)

        self.owner_ms = make_membership(self.project, self.owner_user, 'owner')
        self.manager_ms = make_membership(self.project, self.manager_user, 'manager')
        self.developer_ms = make_membership(self.project, self.developer_user, 'developer')
        self.viewer_ms = make_membership(self.project, self.viewer_user, 'viewer')


class CanViewProjectTest(ProjectPermissionBaseTest):
    def test_all_roles_can_view(self):
        for ms in [self.owner_ms, self.manager_ms, self.developer_ms, self.viewer_ms]:
            with self.subTest(role=ms.role):
                self.assertTrue(can_view_project(ms))

    def test_none_cannot_view(self):
        self.assertFalse(can_view_project(None))


class CanEditProjectTest(ProjectPermissionBaseTest):
    def test_owner_can_edit(self):
        self.assertTrue(can_edit_project(self.owner_ms))

    def test_manager_can_edit(self):
        self.assertTrue(can_edit_project(self.manager_ms))

    def test_developer_cannot_edit(self):
        self.assertFalse(can_edit_project(self.developer_ms))

    def test_viewer_cannot_edit(self):
        self.assertFalse(can_edit_project(self.viewer_ms))

    def test_none_cannot_edit(self):
        self.assertFalse(can_edit_project(None))


class CanDeleteProjectTest(ProjectPermissionBaseTest):
    def test_owner_can_delete(self):
        self.assertTrue(can_delete_project(self.owner_ms))

    def test_manager_cannot_delete(self):
        self.assertFalse(can_delete_project(self.manager_ms))

    def test_developer_cannot_delete(self):
        self.assertFalse(can_delete_project(self.developer_ms))

    def test_viewer_cannot_delete(self):
        self.assertFalse(can_delete_project(self.viewer_ms))

    def test_none_cannot_delete(self):
        self.assertFalse(can_delete_project(None))


class CanManageMembersTest(ProjectPermissionBaseTest):
    def test_owner_can_manage_members(self):
        self.assertTrue(can_manage_members(self.owner_ms))

    def test_manager_can_manage_members(self):
        self.assertTrue(can_manage_members(self.manager_ms))

    def test_developer_cannot_manage_members(self):
        self.assertFalse(can_manage_members(self.developer_ms))

    def test_viewer_cannot_manage_members(self):
        self.assertFalse(can_manage_members(self.viewer_ms))


class CanManageSprintsTest(ProjectPermissionBaseTest):
    def test_owner_can_manage_sprints(self):
        self.assertTrue(can_manage_sprints(self.owner_ms))

    def test_manager_can_manage_sprints(self):
        self.assertTrue(can_manage_sprints(self.manager_ms))

    def test_developer_cannot_manage_sprints(self):
        self.assertFalse(can_manage_sprints(self.developer_ms))

    def test_viewer_cannot_manage_sprints(self):
        self.assertFalse(can_manage_sprints(self.viewer_ms))


class CanCreateTaskTest(ProjectPermissionBaseTest):
    def test_owner_can_create(self):
        self.assertTrue(can_create_task(self.owner_ms))

    def test_manager_can_create(self):
        self.assertTrue(can_create_task(self.manager_ms))

    def test_developer_can_create(self):
        self.assertTrue(can_create_task(self.developer_ms))

    def test_viewer_cannot_create(self):
        self.assertFalse(can_create_task(self.viewer_ms))

    def test_none_cannot_create(self):
        self.assertFalse(can_create_task(None))


class CanEditTaskTest(ProjectPermissionBaseTest):
    def test_owner_can_edit(self):
        self.assertTrue(can_edit_task(self.owner_ms))

    def test_manager_can_edit(self):
        self.assertTrue(can_edit_task(self.manager_ms))

    def test_developer_can_edit(self):
        self.assertTrue(can_edit_task(self.developer_ms))

    def test_viewer_cannot_edit(self):
        self.assertFalse(can_edit_task(self.viewer_ms))

    def test_none_cannot_edit(self):
        self.assertFalse(can_edit_task(None))


class CanDeleteTaskTest(ProjectPermissionBaseTest):
    def test_owner_can_delete(self):
        self.assertTrue(can_delete_task(self.owner_ms))

    def test_manager_can_delete(self):
        self.assertTrue(can_delete_task(self.manager_ms))

    def test_developer_can_delete(self):
        self.assertTrue(can_delete_task(self.developer_ms))

    def test_viewer_cannot_delete(self):
        self.assertFalse(can_delete_task(self.viewer_ms))


class CanManageTagsTest(ProjectPermissionBaseTest):
    def test_owner_can_manage_tags(self):
        self.assertTrue(can_manage_tags(self.owner_ms))

    def test_manager_can_manage_tags(self):
        self.assertTrue(can_manage_tags(self.manager_ms))

    def test_developer_cannot_manage_tags(self):
        self.assertFalse(can_manage_tags(self.developer_ms))

    def test_viewer_cannot_manage_tags(self):
        self.assertFalse(can_manage_tags(self.viewer_ms))


class CanUpdateTaskStatusTest(ProjectPermissionBaseTest):
    def test_mirrors_can_edit_task(self):
        self.assertEqual(
            can_update_task_status(self.owner_ms), can_edit_task(self.owner_ms)
        )
        self.assertEqual(
            can_update_task_status(self.viewer_ms), can_edit_task(self.viewer_ms)
        )


class CanLogTimeTest(ProjectPermissionBaseTest):
    def test_owner_can_log(self):
        self.assertTrue(can_log_time(self.owner_ms))

    def test_manager_can_log(self):
        self.assertTrue(can_log_time(self.manager_ms))

    def test_developer_can_log(self):
        self.assertTrue(can_log_time(self.developer_ms))

    def test_viewer_cannot_log(self):
        self.assertFalse(can_log_time(self.viewer_ms))

    def test_none_cannot_log(self):
        self.assertFalse(can_log_time(None))


class CanUploadAttachmentTest(ProjectPermissionBaseTest):
    def test_owner_can_upload(self):
        self.assertTrue(can_upload_attachment(self.owner_ms))

    def test_manager_can_upload(self):
        self.assertTrue(can_upload_attachment(self.manager_ms))

    def test_developer_can_upload(self):
        self.assertTrue(can_upload_attachment(self.developer_ms))

    def test_viewer_cannot_upload(self):
        self.assertFalse(can_upload_attachment(self.viewer_ms))
