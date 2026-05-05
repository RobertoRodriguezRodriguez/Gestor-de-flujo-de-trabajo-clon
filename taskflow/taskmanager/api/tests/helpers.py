from accounts.models import User
from organizations.models import Organization, OrganizationUser
from projects.models import Project, ProjectMember
from tasks.models import Task
from rest_framework_simplejwt.tokens import RefreshToken


def make_user(n=1, email=None, password='testpass1!'):
    email = email or f'user{n}@example.com'
    return User.objects.create_user(email=email, name=f'User {n}', password=password)


def make_org(name='Test Org'):
    return Organization.objects.create(name=name)


def add_org_member(org, user, role='member'):
    return OrganizationUser.objects.create(organization=org, user=user, role=role)


def make_project(org, owner=None, key='TP', name='Test Project'):
    return Project.objects.create(
        organization=org, owner=owner, name=name, key=key
    )


def add_project_member(project, user, role='developer'):
    return ProjectMember.objects.create(project=project, user=user, role=role)


def make_task(project, title='Test Task', status='backlog'):
    return Task.objects.create(project=project, title=title, status=status)


def get_access_token(user):
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token), str(refresh)
