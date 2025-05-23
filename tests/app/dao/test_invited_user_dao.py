import uuid
from datetime import timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm.exc import NoResultFound

from app import db
from app.dao.invited_user_dao import (
    expire_invitations_created_more_than_two_days_ago,
    get_invited_user_by_id,
    get_invited_user_by_service_and_id,
    get_invited_users_for_service,
    save_invited_user,
)
from app.enums import InvitedUserStatus, PermissionType
from app.models import InvitedUser
from app.utils import utc_now
from tests.app.db import create_invited_user


def _get_invited_user_count():
    stmt = select(func.count()).select_from(InvitedUser)
    return db.session.execute(stmt).scalar() or 0


def test_create_invited_user(notify_db_session, sample_service):
    assert _get_invited_user_count() == 0
    email_address = "invited_user@service.gov.uk"
    invite_from = sample_service.users[0]

    data = {
        "service": sample_service,
        "email_address": email_address,
        "from_user": invite_from,
        "permissions": "send_emails,manage_settings",
        "folder_permissions": [],
    }

    invited_user = InvitedUser(**data)
    save_invited_user(invited_user)

    assert _get_invited_user_count() == 1
    assert invited_user.email_address == email_address
    assert invited_user.from_user == invite_from
    permissions = invited_user.get_permissions()
    assert len(permissions) == 2
    assert PermissionType.SEND_EMAILS in permissions
    assert PermissionType.MANAGE_SETTINGS in permissions
    assert invited_user.folder_permissions == []


def test_create_invited_user_sets_default_folder_permissions_of_empty_list(
    sample_service,
):
    assert _get_invited_user_count() == 0
    invite_from = sample_service.users[0]

    data = {
        "service": sample_service,
        "email_address": "invited_user@service.gov.uk",
        "from_user": invite_from,
        "permissions": "send_messages,manage_service",
    }

    invited_user = InvitedUser(**data)
    save_invited_user(invited_user)

    assert _get_invited_user_count() == 1
    assert invited_user.folder_permissions == []


def test_get_invited_user_by_service_and_id(notify_db_session, sample_invited_user):
    from_db = get_invited_user_by_service_and_id(
        sample_invited_user.service.id, sample_invited_user.id
    )
    assert from_db == sample_invited_user


def test_get_invited_user_by_id(notify_db_session, sample_invited_user):
    from_db = get_invited_user_by_id(sample_invited_user.id)
    assert from_db == sample_invited_user


def test_get_unknown_invited_user_returns_none(notify_db_session, sample_service):
    unknown_id = uuid.uuid4()

    with pytest.raises(NoResultFound) as e:
        get_invited_user_by_service_and_id(sample_service.id, unknown_id)
    assert "No row was found when one was required" in str(e.value)


def test_get_invited_users_for_service(notify_db_session, sample_service):
    invites = []
    for i in range(0, 5):
        email = "invited_user_{}@service.gov.uk".format(i)

        invited_user = create_invited_user(sample_service, to_email_address=email)
        invites.append(invited_user)

    all_from_db = get_invited_users_for_service(sample_service.id)
    assert len(all_from_db) == 5
    for invite in invites:
        assert invite in all_from_db


def test_get_invited_users_for_service_that_has_no_invites(
    notify_db_session, sample_service
):
    invites = get_invited_users_for_service(sample_service.id)
    assert len(invites) == 0


def test_save_invited_user_sets_status_to_cancelled(
    notify_db_session, sample_invited_user
):
    assert _get_invited_user_count() == 1
    saved = db.session.get(InvitedUser, sample_invited_user.id)
    assert saved.status == InvitedUserStatus.PENDING
    saved.status = InvitedUserStatus.CANCELLED
    save_invited_user(saved)
    assert _get_invited_user_count() == 1
    cancelled_invited_user = db.session.get(InvitedUser, sample_invited_user.id)
    assert cancelled_invited_user.status == InvitedUserStatus.CANCELLED


def test_should_delete_all_invitations_more_than_one_day_old(
    sample_user, sample_service
):
    make_invitation(sample_user, sample_service, age=timedelta(hours=48))
    make_invitation(sample_user, sample_service, age=timedelta(hours=48))
    stmt = select(InvitedUser).where(InvitedUser.status != InvitedUserStatus.EXPIRED)
    result = db.session.execute(stmt).scalars().all()
    assert len(result) == 2
    expire_invitations_created_more_than_two_days_ago()
    stmt = (
        select(func.count())
        .select_from(InvitedUser)
        .where(InvitedUser.status != InvitedUserStatus.EXPIRED)
    )
    count = db.session.execute(stmt).scalar() or 0
    assert count == 0


def test_should_not_delete_invitations_less_than_two_days_old(
    sample_user, sample_service
):
    two_days = timedelta(days=2)
    one_second = timedelta(seconds=1)
    make_invitation(
        sample_user,
        sample_service,
        age=two_days - one_second,  # Not quite two days
        email_address="valid@2.com",
    )
    make_invitation(
        sample_user,
        sample_service,
        age=two_days,
        email_address="expired@1.com",
    )

    stmt = (
        select(func.count())
        .select_from(InvitedUser)
        .where(InvitedUser.status != InvitedUserStatus.EXPIRED)
    )
    count = db.session.execute(stmt).scalar() or 0
    assert count == 2
    expire_invitations_created_more_than_two_days_ago()
    stmt = (
        select(func.count())
        .select_from(InvitedUser)
        .where(InvitedUser.status != InvitedUserStatus.EXPIRED)
    )
    count = db.session.execute(stmt).scalar() or 0
    assert count == 1
    stmt = select(InvitedUser).where(InvitedUser.status != InvitedUserStatus.EXPIRED)
    invited_user = db.session.execute(stmt).scalars().first()
    assert invited_user.email_address == "valid@2.com"
    stmt = select(InvitedUser).where(InvitedUser.status == InvitedUserStatus.EXPIRED)
    invited_user = db.session.execute(stmt).scalars().first()

    assert invited_user.email_address == "expired@1.com"


def make_invitation(user, service, age=None, email_address="test@test.com"):
    verify_code = InvitedUser(
        email_address=email_address,
        from_user=user,
        service=service,
        status=InvitedUserStatus.PENDING,
        created_at=utc_now() - (age or timedelta(hours=0)),
        permissions=PermissionType.MANAGE_SETTINGS,
        folder_permissions=[str(uuid.uuid4())],
    )
    db.session.add(verify_code)
    db.session.commit()
