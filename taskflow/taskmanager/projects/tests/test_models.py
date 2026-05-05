from django.test import TestCase

from accounts.models import User
from organizations.models import Organization
from projects.models import Project, ProjectMember
from tasks.models import Task, TimeLog


def make_user():
    return User.objects.create_user(
        email='user@example.com', name='Test User', password='pass'
    )


def make_project(budget=None):
    org = Organization.objects.create(name='Org')
    return Project.objects.create(
        organization=org, name='Project', key='PR', hour_budget=budget
    )


class ProjectGetTaskStatsTest(TestCase):
    def setUp(self):
        self.project = make_project()

    def test_empty_project(self):
        stats = self.project.get_task_stats()
        self.assertEqual(stats['total'], 0)
        self.assertEqual(stats['done'], 0)
        self.assertEqual(stats['progress'], 0)

    def test_all_tasks_done(self):
        Task.objects.create(project=self.project, title='T1', status='done')
        Task.objects.create(project=self.project, title='T2', status='done')
        stats = self.project.get_task_stats()
        self.assertEqual(stats['total'], 2)
        self.assertEqual(stats['done'], 2)
        self.assertEqual(stats['progress'], 100)

    def test_half_tasks_done(self):
        Task.objects.create(project=self.project, title='T1', status='done')
        Task.objects.create(project=self.project, title='T2', status='todo')
        stats = self.project.get_task_stats()
        self.assertEqual(stats['total'], 2)
        self.assertEqual(stats['done'], 1)
        self.assertEqual(stats['progress'], 50)

    def test_no_tasks_done(self):
        Task.objects.create(project=self.project, title='T1', status='in_progress')
        stats = self.project.get_task_stats()
        self.assertEqual(stats['done'], 0)
        self.assertEqual(stats['progress'], 0)


class ProjectGetHourStatsTest(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_no_budget_no_logs(self):
        project = make_project(budget=None)
        stats = project.get_hour_stats()
        self.assertIsNone(stats['budget'])
        self.assertEqual(stats['consumed'], 0)
        self.assertIsNone(stats['remaining'])
        self.assertEqual(stats['pct'], 0)

    def test_with_budget_and_logs(self):
        project = make_project(budget=10)
        task = Task.objects.create(project=project, title='Task')
        TimeLog.objects.create(
            task=task, project=project, user=self.user, hours=4
        )
        stats = project.get_hour_stats()
        self.assertEqual(stats['budget'], 10)
        self.assertEqual(stats['consumed'], 4)
        self.assertEqual(stats['remaining'], 6)
        self.assertEqual(stats['pct'], 40)

    def test_consumed_exceeds_budget_caps_at_100_pct(self):
        project = make_project(budget=5)
        task = Task.objects.create(project=project, title='Task')
        TimeLog.objects.create(
            task=task, project=project, user=self.user, hours=10
        )
        stats = project.get_hour_stats()
        self.assertEqual(stats['pct'], 100)

    def test_str_representation(self):
        project = make_project()
        self.assertIn('PR', str(project))
        self.assertIn('Project', str(project))


class ProjectSoftDeleteTest(TestCase):
    def test_soft_delete_sets_deleted_at(self):
        project = make_project()
        self.assertIsNone(project.deleted_at)
        project.soft_delete()
        project.refresh_from_db()
        self.assertIsNotNone(project.deleted_at)
