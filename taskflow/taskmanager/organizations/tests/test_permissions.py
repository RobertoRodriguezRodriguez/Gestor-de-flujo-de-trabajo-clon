from django.test import TestCase

from accounts.models import User
from organizations.models import Organization, OrganizationUser
from organizations.permissions import (
    can_manage_members,
    can_assign_role,
    can_delete_org,
    can_view_org,
    is_last_owner,
)


def make_user(n=1):
    return User.objects.create_user(
        email=f'user{n}@example.com', name=f'User {n}', password='pass'
    )


def make_org(name='Test Org'):
    return Organization.objects.create(name=name)


def make_membership(org, user, role):
    return OrganizationUser.objects.create(organization=org, user=user, role=role)


class CanManageMembersTest(TestCase):
    def setUp(self):
        self.org = make_org()
        self.owner = make_user(1)
        self.admin = make_user(2)
        self.member = make_user(3)
        self.owner_ms = make_membership(self.org, self.owner, 'owner')
        self.admin_ms = make_membership(self.org, self.admin, 'admin')
        self.member_ms = make_membership(self.org, self.member, 'member')

    def test_owner_can_manage(self):
        self.assertTrue(can_manage_members(self.owner_ms))

    def test_admin_can_manage(self):
        self.assertTrue(can_manage_members(self.admin_ms))

    def test_member_cannot_manage(self):
        self.assertFalse(can_manage_members(self.member_ms))

    def test_none_cannot_manage(self):
        self.assertFalse(can_manage_members(None))


class CanAssignRoleTest(TestCase):
    def setUp(self):
        self.org = make_org()
        self.owner = make_user(1)
        self.admin = make_user(2)
        self.member = make_user(3)
        self.owner_ms = make_membership(self.org, self.owner, 'owner')
        self.admin_ms = make_membership(self.org, self.admin, 'admin')
        self.member_ms = make_membership(self.org, self.member, 'member')

    def test_owner_can_assign_owner_role(self):
        self.assertTrue(can_assign_role(self.owner_ms, 'owner'))

    def test_admin_cannot_assign_owner_role(self):
        self.assertFalse(can_assign_role(self.admin_ms, 'owner'))

    def test_member_cannot_assign_owner_role(self):
        self.assertFalse(can_assign_role(self.member_ms, 'owner'))

    def test_owner_can_assign_admin_role(self):
        self.assertTrue(can_assign_role(self.owner_ms, 'admin'))

    def test_admin_can_assign_admin_role(self):
        self.assertTrue(can_assign_role(self.admin_ms, 'admin'))

    def test_member_cannot_assign_admin_role(self):
        self.assertFalse(can_assign_role(self.member_ms, 'admin'))

    def test_owner_can_assign_member_role(self):
        self.assertTrue(can_assign_role(self.owner_ms, 'member'))

    def test_admin_can_assign_member_role(self):
        self.assertTrue(can_assign_role(self.admin_ms, 'member'))

    def test_none_cannot_assign_any_role(self):
        self.assertFalse(can_assign_role(None, 'member'))


class CanDeleteOrgTest(TestCase):
    def setUp(self):
        self.org = make_org()
        self.owner = make_user(1)
        self.admin = make_user(2)
        self.member = make_user(3)
        self.owner_ms = make_membership(self.org, self.owner, 'owner')
        self.admin_ms = make_membership(self.org, self.admin, 'admin')
        self.member_ms = make_membership(self.org, self.member, 'member')

    def test_owner_can_delete(self):
        self.assertTrue(can_delete_org(self.owner_ms))

    def test_admin_cannot_delete(self):
        self.assertFalse(can_delete_org(self.admin_ms))

    def test_member_cannot_delete(self):
        self.assertFalse(can_delete_org(self.member_ms))

    def test_none_cannot_delete(self):
        self.assertFalse(can_delete_org(None))


class CanViewOrgTest(TestCase):
    def setUp(self):
        self.org = make_org()
        self.user = make_user(1)
        self.membership = make_membership(self.org, self.user, 'member')

    def test_member_can_view(self):
        self.assertTrue(can_view_org(self.membership))

    def test_none_cannot_view(self):
        self.assertFalse(can_view_org(None))


class IsLastOwnerTest(TestCase):
    def setUp(self):
        self.org = make_org()

    def test_single_owner_is_last(self):
        owner = make_user(1)
        make_membership(self.org, owner, 'owner')
        self.assertTrue(is_last_owner(self.org))

    def test_two_owners_not_last(self):
        owner1 = make_user(1)
        owner2 = make_user(2)
        make_membership(self.org, owner1, 'owner')
        make_membership(self.org, owner2, 'owner')
        self.assertFalse(is_last_owner(self.org))

    def test_no_owners_returns_false(self):
        member = make_user(1)
        make_membership(self.org, member, 'member')
        self.assertFalse(is_last_owner(self.org))
