from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from organizations.models import Organization
from projects.models import Project
from tasks.models import Task, Tag, Comment, TimeLog


def make_user(n=1):
    return User.objects.create_user(
        email=f'user{n}@example.com', name=f'User {n}', password='pass'
    )


def make_project():
    org = Organization.objects.create(name='Org')
    return Project.objects.create(organization=org, name='Project', key='PR')


def make_task(project, title='Task', status='backlog', **kwargs):
    return Task.objects.create(project=project, title=title, status=status, **kwargs)


class TaskProjectSequenceTest(TestCase):
    def setUp(self):
        self.project = make_project()

    def test_first_task_gets_sequence_1(self):
        task = make_task(self.project)
        self.assertEqual(task.project_sequence, 1)

    def test_second_task_gets_sequence_2(self):
        make_task(self.project, title='T1')
        task2 = make_task(self.project, title='T2')
        self.assertEqual(task2.project_sequence, 2)

    def test_sequence_is_per_project(self):
        org = Organization.objects.create(name='Org2')
        project2 = Project.objects.create(organization=org, name='Other', key='OT')
        make_task(self.project, title='T1')
        task_other = make_task(project2, title='T1')
        self.assertEqual(task_other.project_sequence, 1)

    def test_explicit_sequence_is_not_overwritten(self):
        task = Task.objects.create(
            project=self.project, title='Manual', project_sequence=99
        )
        self.assertEqual(task.project_sequence, 99)

    def test_str_includes_key_and_sequence(self):
        task = make_task(self.project)
        self.assertIn('PR-1', str(task))
        self.assertIn('Task', str(task))


class TaskCompletedAtTest(TestCase):
    def setUp(self):
        self.project = make_project()

    def test_completed_at_set_when_status_done(self):
        task = make_task(self.project, status='in_progress')
        self.assertIsNone(task.completed_at)
        task.status = 'done'
        task.save()
        task.refresh_from_db()
        self.assertIsNotNone(task.completed_at)

    def test_completed_at_cleared_when_reopened(self):
        task = make_task(self.project, status='done')
        self.assertIsNotNone(task.completed_at)
        task.status = 'in_progress'
        task.save()
        task.refresh_from_db()
        self.assertIsNone(task.completed_at)

    def test_completed_at_not_overwritten_on_resave(self):
        task = make_task(self.project, status='done')
        first_completed_at = task.completed_at
        task.title = 'Updated Title'
        task.save()
        task.refresh_from_db()
        self.assertEqual(task.completed_at, first_completed_at)


class TaskIsOverdueTest(TestCase):
    def setUp(self):
        self.project = make_project()

    def test_past_due_date_not_done_is_overdue(self):
        yesterday = date.today() - timedelta(days=1)
        task = make_task(self.project, status='in_progress', due_date=yesterday)
        self.assertTrue(task.is_overdue())

    def test_future_due_date_not_overdue(self):
        tomorrow = date.today() + timedelta(days=1)
        task = make_task(self.project, status='in_progress', due_date=tomorrow)
        self.assertFalse(task.is_overdue())

    def test_done_task_never_overdue(self):
        yesterday = date.today() - timedelta(days=1)
        task = make_task(self.project, status='done', due_date=yesterday)
        self.assertFalse(task.is_overdue())

    def test_no_due_date_never_overdue(self):
        task = make_task(self.project, status='in_progress')
        self.assertFalse(task.is_overdue())


class TaskGetTotalLoggedHoursTest(TestCase):
    def setUp(self):
        self.project = make_project()
        self.user = make_user()
        self.task = make_task(self.project)

    def test_no_logs_returns_zero(self):
        self.assertEqual(self.task.get_total_logged_hours(), 0)

    def test_single_log(self):
        TimeLog.objects.create(
            task=self.task, project=self.project, user=self.user, hours=3.5
        )
        self.assertEqual(self.task.get_total_logged_hours(), 3.5)

    def test_multiple_logs_are_summed(self):
        TimeLog.objects.create(
            task=self.task, project=self.project, user=self.user, hours=2
        )
        TimeLog.objects.create(
            task=self.task, project=self.project, user=self.user, hours=1.5
        )
        self.assertEqual(self.task.get_total_logged_hours(), 3.5)


class TimeLogHoursDisplayTest(TestCase):
    def setUp(self):
        self.project = make_project()
        self.user = make_user()
        self.task = make_task(self.project)

    def _make_log(self, hours):
        return TimeLog(
            task=self.task, project=self.project, user=self.user, hours=hours
        )

    def test_whole_hours(self):
        self.assertEqual(self._make_log(3).hours_display, '3h')

    def test_hours_and_minutes(self):
        self.assertEqual(self._make_log(1.5).hours_display, '1h 30m')

    def test_quarter_hour(self):
        self.assertEqual(self._make_log(0.25).hours_display, '0h 15m')


class CommentSoftDeleteTest(TestCase):
    def setUp(self):
        self.project = make_project()
        self.user = make_user()
        self.task = make_task(self.project)

    def test_comment_has_no_deleted_at_by_default(self):
        comment = Comment.objects.create(
            task=self.task, user=self.user, content='Hello'
        )
        self.assertIsNone(comment.deleted_at)

    def test_soft_deleted_comment_can_be_filtered_out(self):
        c1 = Comment.objects.create(task=self.task, user=self.user, content='Active')
        c2 = Comment.objects.create(task=self.task, user=self.user, content='Deleted')
        c2.deleted_at = timezone.now()
        c2.save()

        active = self.task.comments.filter(deleted_at__isnull=True)
        self.assertIn(c1, active)
        self.assertNotIn(c2, active)


class TagTest(TestCase):
    def setUp(self):
        self.project = make_project()

    def test_tag_str(self):
        tag = Tag.objects.create(project=self.project, name='frontend', color='#6366f1')
        self.assertEqual(str(tag), 'frontend')

    def test_tag_unique_per_project(self):
        Tag.objects.create(project=self.project, name='bug', color='#ff0000')
        with self.assertRaises(Exception):
            Tag.objects.create(project=self.project, name='bug', color='#ff0000')
