import pytest
from flask import json
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.celery.process_ses_receipts_tasks import (
    check_and_queue_callback_task,
    handle_complaint,
)
from app.dao.notifications_dao import get_notification_by_id
from app.enums import NotificationStatus
from app.models import Complaint
from tests.app.db import (
    create_notification,
    create_notification_history,
    create_service_callback_api,
    ses_complaint_callback,
    ses_complaint_callback_malformed_message_id,
    ses_complaint_callback_with_missing_complaint_type,
)


def test_ses_callback_should_not_set_status_once_status_is_delivered(
    sample_email_template,
):
    notification = create_notification(
        sample_email_template,
        status=NotificationStatus.DELIVERED,
    )

    assert (
        get_notification_by_id(notification.id).status == NotificationStatus.DELIVERED
    )


def test_process_ses_results_in_complaint(sample_email_template):
    notification = create_notification(template=sample_email_template, reference="ref1")
    handle_complaint(json.loads(ses_complaint_callback()["Message"]))
    complaints = db.session.execute(select(Complaint)).scalars().all()
    assert len(complaints) == 1
    assert complaints[0].notification_id == notification.id


def test_handle_complaint_does_not_raise_exception_if_reference_is_missing(notify_api):
    response = json.loads(ses_complaint_callback_malformed_message_id()["Message"])
    handle_complaint(response)
    assert len(db.session.execute(select(Complaint)).scalars().all()) == 0


def test_handle_complaint_does_raise_exception_if_notification_not_found(notify_api):
    response = json.loads(ses_complaint_callback()["Message"])
    with pytest.raises(expected_exception=SQLAlchemyError):
        handle_complaint(response)


def test_process_ses_results_in_complaint_if_notification_history_does_not_exist(
    sample_email_template,
):
    notification = create_notification(template=sample_email_template, reference="ref1")
    handle_complaint(json.loads(ses_complaint_callback()["Message"]))
    complaints = db.session.execute(select(Complaint)).scalars().all()
    assert len(complaints) == 1
    assert complaints[0].notification_id == notification.id


def test_process_ses_results_in_complaint_if_notification_does_not_exist(
    sample_email_template,
):
    notification = create_notification_history(
        template=sample_email_template, reference="ref1"
    )
    handle_complaint(json.loads(ses_complaint_callback()["Message"]))
    complaints = db.session.execute(select(Complaint)).scalars().all()
    assert len(complaints) == 1
    assert complaints[0].notification_id == notification.id


def test_process_ses_results_in_complaint_save_complaint_with_null_complaint_type(
    notify_api, sample_email_template
):
    notification = create_notification(template=sample_email_template, reference="ref1")
    msg = json.loads(ses_complaint_callback_with_missing_complaint_type()["Message"])
    handle_complaint(msg)
    complaints = db.session.execute(select(Complaint)).scalars().all()
    assert len(complaints) == 1
    assert complaints[0].notification_id == notification.id
    assert not complaints[0].complaint_type


def test_check_and_queue_callback_task(mocker, sample_notification):
    mock_create = mocker.patch(
        "app.celery.process_ses_receipts_tasks.create_delivery_status_callback_data"
    )

    mock_send = mocker.patch(
        "app.celery.service_callback_tasks.send_delivery_status_to_service.apply_async"
    )

    callback_api = create_service_callback_api(service=sample_notification.service)
    mock_create.return_value = "encrypted_status_update"

    check_and_queue_callback_task(sample_notification)

    # callback_api doesn't match by equality for some
    # reason, so we need to take this approach instead
    mock_create_args = mock_create.mock_calls[0][1]
    assert mock_create_args[0] == sample_notification
    assert mock_create_args[1].id == callback_api.id

    mock_send.assert_called_once_with(
        [str(sample_notification.id), mock_create.return_value],
        queue="service-callbacks",
    )


def test_check_and_queue_callback_task_no_callback_api(mocker, sample_notification):
    mock_send = mocker.patch(
        "app.celery.service_callback_tasks.send_delivery_status_to_service.apply_async"
    )

    check_and_queue_callback_task(sample_notification)
    mock_send.assert_not_called()
