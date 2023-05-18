from datetime import datetime, timedelta

import pytest
from freezegun import freeze_time

from app.dao.uploads_dao import dao_get_uploads_by_service_id
from app.models import JOB_STATUS_IN_PROGRESS, LETTER_TYPE
from tests.app.db import (
    create_job,
    create_notification,
    create_service,
    create_service_data_retention,
    create_template,
)


def create_uploaded_letter(letter_template, service, status='created', created_at=None):
    return create_notification(
        template=letter_template,
        to_field="file-name",
        status=status,
        reference="dvla-reference",
        client_reference="file-name",
        one_off=True,
        created_by_id=service.users[0].id,
        created_at=created_at
    )


def create_uploaded_template(service):
    return create_template(
        service,
        template_type=LETTER_TYPE,
        template_name='Pre-compiled PDF',
        subject='Pre-compiled PDF',
        content="",
        hidden=True,
    )


@freeze_time("2020-02-02 09:00")  # GMT time
def test_get_uploads_for_service(sample_template):
    create_service_data_retention(sample_template.service, 'sms', days_of_retention=9)
    job = create_job(sample_template, processing_started=datetime.utcnow())

    other_service = create_service(service_name="other service")
    other_template = create_template(service=other_service)
    other_job = create_job(other_template, processing_started=datetime.utcnow())

    uploads_from_db = dao_get_uploads_by_service_id(job.service_id).items
    other_uploads_from_db = dao_get_uploads_by_service_id(other_job.service_id).items

    assert len(uploads_from_db) == 1

    assert uploads_from_db[0] == (
        job.id,
        job.original_file_name,
        job.notification_count,
        'sms',
        9,
        job.created_at,
        job.scheduled_for,
        job.processing_started,
        job.job_status,
        "job",
        None,
    )

    assert len(other_uploads_from_db) == 1
    assert other_uploads_from_db[0] == (other_job.id,
                                        other_job.original_file_name,
                                        other_job.notification_count,
                                        other_job.template.template_type,
                                        7,
                                        other_job.created_at,
                                        other_job.scheduled_for,
                                        other_job.processing_started,
                                        other_job.job_status,
                                        "job",
                                        None)

    assert uploads_from_db[0] != other_uploads_from_db[0]


def test_get_uploads_orders_by_processing_started_desc(sample_template):
    days_ago = datetime.utcnow() - timedelta(days=3)
    upload_1 = create_job(sample_template, processing_started=datetime.utcnow() - timedelta(days=1),
                          created_at=days_ago,
                          job_status=JOB_STATUS_IN_PROGRESS)
    upload_2 = create_job(sample_template, processing_started=datetime.utcnow() - timedelta(days=2),
                          created_at=days_ago,
                          job_status=JOB_STATUS_IN_PROGRESS)

    results = dao_get_uploads_by_service_id(service_id=sample_template.service_id).items

    assert len(results) == 2
    assert results[0].id == upload_1.id
    assert results[1].id == upload_2.id


@pytest.mark.skip(reason="Investigate what remains after removing letters")
@freeze_time("2020-10-27 16:15")  # GMT time
def test_get_uploads_orders_by_processing_started_and_created_at_desc(sample_template):
    letter_template = create_uploaded_template(sample_template.service)

    days_ago = datetime.utcnow() - timedelta(days=4)
    create_uploaded_letter(letter_template, service=letter_template.service)
    upload_2 = create_job(sample_template, processing_started=datetime.utcnow() - timedelta(days=1),
                          created_at=days_ago,
                          job_status=JOB_STATUS_IN_PROGRESS)
    upload_3 = create_job(sample_template, processing_started=datetime.utcnow() - timedelta(days=2),
                          created_at=days_ago,
                          job_status=JOB_STATUS_IN_PROGRESS)
    create_uploaded_letter(letter_template, service=letter_template.service,
                           created_at=datetime.utcnow() - timedelta(days=3))

    results = dao_get_uploads_by_service_id(service_id=sample_template.service_id).items

    assert len(results) == 4
    assert results[0].id is None
    assert results[1].id == upload_2.id
    assert results[2].id == upload_3.id
    assert results[3].id is None


@pytest.mark.skip(reason="Investigate what remains after removing letters")
@freeze_time('2020-04-02 14:00')  # Few days after the clocks go forward
def test_get_uploads_only_gets_uploads_within_service_retention_period(sample_template):
    letter_template = create_uploaded_template(sample_template.service)
    create_service_data_retention(sample_template.service, 'sms', days_of_retention=3)

    days_ago = datetime.utcnow() - timedelta(days=4)
    upload_1 = create_uploaded_letter(letter_template, service=letter_template.service)
    upload_2 = create_job(
        sample_template, processing_started=datetime.utcnow() - timedelta(days=1), created_at=days_ago,
        job_status=JOB_STATUS_IN_PROGRESS
    )
    # older than custom retention for sms:
    create_job(
        sample_template, processing_started=datetime.utcnow() - timedelta(days=5), created_at=days_ago,
        job_status=JOB_STATUS_IN_PROGRESS
    )
    upload_3 = create_uploaded_letter(
        letter_template, service=letter_template.service, created_at=datetime.utcnow() - timedelta(days=3)
    )

    # older than retention for sms but within letter retention:
    upload_4 = create_uploaded_letter(
        letter_template, service=letter_template.service, created_at=datetime.utcnow() - timedelta(days=6)
    )

    # older than default retention for letters:
    create_uploaded_letter(
        letter_template, service=letter_template.service, created_at=datetime.utcnow() - timedelta(days=8)
    )

    results = dao_get_uploads_by_service_id(service_id=sample_template.service_id).items

    assert len(results) == 4

    # Uploaded letters get their `created_at` shifted time of printing
    # 21:30 EST == 16:30 UTC
    assert results[0].created_at == upload_1.created_at.replace(hour=21, minute=30, second=0, microsecond=0)

    # Jobs keep their original `created_at`
    assert results[1].created_at == upload_2.created_at.replace(hour=14, minute=00, second=0, microsecond=0)

    # Still in BST here…
    assert results[2].created_at == upload_3.created_at.replace(hour=21, minute=30, second=0, microsecond=0)

    # Now we’ve gone far enough back to be in GMT
    # 17:30 GMT == 17:30 UTC
    assert results[3].created_at == upload_4.created_at.replace(hour=21, minute=30, second=0, microsecond=0)


@pytest.mark.skip(reason="Investigate what remains after removing letters")
@freeze_time('2020-02-02 14:00')
def test_get_uploads_is_paginated(sample_template):
    letter_template = create_uploaded_template(sample_template.service)

    create_uploaded_letter(
        letter_template, sample_template.service, status='delivered',
        created_at=datetime.utcnow() - timedelta(minutes=3),
    )
    create_job(
        sample_template, processing_started=datetime.utcnow() - timedelta(minutes=2),
        job_status=JOB_STATUS_IN_PROGRESS,
    )
    create_uploaded_letter(
        letter_template, sample_template.service, status='delivered',
        created_at=datetime.utcnow() - timedelta(minutes=1),
    )
    create_job(
        sample_template, processing_started=datetime.utcnow(),
        job_status=JOB_STATUS_IN_PROGRESS,
    )

    results = dao_get_uploads_by_service_id(sample_template.service_id, page=1, page_size=1)

    assert results.per_page == 1
    assert results.total == 3
    assert len(results.items) == 1
    assert results.items[0].created_at == datetime.utcnow().replace(hour=22, minute=30, second=0, microsecond=0)
    assert results.items[0].notification_count == 2
    assert results.items[0].upload_type == 'letter_day'

    results = dao_get_uploads_by_service_id(sample_template.service_id, page=2, page_size=1)

    assert len(results.items) == 1
    assert results.items[0].created_at == datetime.utcnow().replace(hour=14, minute=0, second=0, microsecond=0)
    assert results.items[0].notification_count == 1
    assert results.items[0].upload_type == 'job'


def test_get_uploads_returns_empty_list(sample_service):
    items = dao_get_uploads_by_service_id(sample_service.id).items
    assert items == []
