import os
from datetime import datetime, timedelta

from flask import current_app
from notifications_utils.clients.zendesk.zendesk_client import NotifySupportTicket
from sqlalchemy import between
from sqlalchemy.exc import SQLAlchemyError

from app import notify_celery, redis_store, zendesk_client
from app.celery.tasks import (
    get_recipient_csv_and_template_and_sender_id,
    process_incomplete_jobs,
    process_job,
    process_row,
)
from app.config import QueueNames
from app.dao.invited_org_user_dao import (
    delete_org_invitations_created_more_than_two_days_ago,
)
from app.dao.invited_user_dao import expire_invitations_created_more_than_two_days_ago
from app.dao.jobs_dao import (
    dao_set_scheduled_jobs_to_pending,
    dao_update_job,
    find_jobs_with_missing_rows,
    find_missing_row_for_job,
)
from app.dao.notifications_dao import (
    dao_get_failed_notification_count,
    notifications_not_yet_sent,
)
from app.dao.services_dao import (
    dao_find_services_sending_to_tv_numbers,
    dao_find_services_with_high_failure_rates,
)
from app.dao.users_dao import delete_codes_older_created_more_than_a_day_ago
from app.delivery.send_to_providers import provider_to_use
from app.models import (
    EMAIL_TYPE,
    JOB_STATUS_ERROR,
    JOB_STATUS_IN_PROGRESS,
    JOB_STATUS_PENDING,
    SMS_TYPE,
    Job,
)
from app.notifications.process_notifications import send_notification_to_queue


@notify_celery.task(name="run-scheduled-jobs")
def run_scheduled_jobs():
    try:
        for job in dao_set_scheduled_jobs_to_pending():
            process_job.apply_async([str(job.id)], queue=QueueNames.JOBS)
            current_app.logger.info(
                "Job ID {} added to process job queue".format(job.id)
            )
    except SQLAlchemyError:
        current_app.logger.exception("Failed to run scheduled jobs")
        raise


@notify_celery.task(name="delete-verify-codes")
def delete_verify_codes():
    try:
        start = datetime.utcnow()
        deleted = delete_codes_older_created_more_than_a_day_ago()
        current_app.logger.info(
            "Delete job started {} finished {} deleted {} verify codes".format(
                start, datetime.utcnow(), deleted
            )
        )
    except SQLAlchemyError:
        current_app.logger.exception("Failed to delete verify codes")
        raise


@notify_celery.task(name="expire-or-delete-invitations")
def expire_or_delete_invitations():
    try:
        start = datetime.utcnow()
        expired_invites = expire_invitations_created_more_than_two_days_ago()
        current_app.logger.info(
            f"Expire job started {start} finished {datetime.utcnow()} expired {expired_invites} invitations"
        )
    except SQLAlchemyError:
        current_app.logger.exception("Failed to expire invitations")
        raise

    try:
        start = datetime.utcnow()
        deleted_invites = delete_org_invitations_created_more_than_two_days_ago()
        current_app.logger.info(
            f"Delete job started {start} finished {datetime.utcnow()} deleted {deleted_invites} invitations"
        )
    except SQLAlchemyError:
        current_app.logger.exception("Failed to delete invitations")
        raise


@notify_celery.task(name="check-db-notification-fails")
def check_db_notification_fails():
    # get values from
    last_value = redis_store.get("LAST_DB_NOTIFICATION_COUNT")

    if not last_value:
        last_value = 0
    # get count from db
    failed_count = dao_get_failed_notification_count()
    # update redis if need be
    if failed_count > last_value:
        redis_store.set("LAST_DB_NOTIFICATION_COUNT", failed_count)
    # TODO send to slack as well
    # Only send the first time if we breach a level, except for case of >= 100%
    message = ""
    if failed_count >= 10000:
        message = "We are over 100% in the db for failed notifications"
    elif failed_count >= 7500 and last_value < 7500:
        message = (
            "tts-notify-alerts@gsa.gov",
            f"We crossed above 75% in the db for failed notifications on {os.getenv('ENVIRONMENT')}",
        )
    elif failed_count >= 5000 and last_value < 5000:
        message = (
            "tts-notify-alerts@gsa.gov",
            f"We crossed above 50% in the db for failed notifications on {os.getenv('ENVIRONMENT')}",
        )
    elif failed_count >= 2500 and last_value < 2500:
        message = (
            "tts-notify-alerts@gsa.gov",
            f"We crossed above 25% in the db for failed notifications on {os.getenv('ENVIRONMENT')}",
        )
    # We don't have permissions to send email in development
    if message and os.getenv("ENVIRONMENT") != "development":
        provider = provider_to_use(EMAIL_TYPE, False)
        provider.send_email(
            "ken.kehl@gsa.gov",
            "ken.kehl@gsa.gov",
            "DB Notification Failures Level Breached",
            body=str(message),
        )


@notify_celery.task(name="check-job-status")
def check_job_status():
    """
    every x minutes do this check
    select
    from jobs
    where job_status == 'in progress'
    and processing started between 30 and 35 minutes ago
    OR where the job_status == 'pending'
    and the job scheduled_for timestamp is between 30 and 35 minutes ago.
    if any results then
        update the job_status to 'error'
        process the rows in the csv that are missing (in another task) just do the check here.
    """
    thirty_minutes_ago = datetime.utcnow() - timedelta(minutes=30)
    thirty_five_minutes_ago = datetime.utcnow() - timedelta(minutes=35)

    incomplete_in_progress_jobs = Job.query.filter(
        Job.job_status == JOB_STATUS_IN_PROGRESS,
        between(Job.processing_started, thirty_five_minutes_ago, thirty_minutes_ago),
    )
    incomplete_pending_jobs = Job.query.filter(
        Job.job_status == JOB_STATUS_PENDING,
        Job.scheduled_for.isnot(None),
        between(Job.scheduled_for, thirty_five_minutes_ago, thirty_minutes_ago),
    )

    jobs_not_complete_after_30_minutes = (
        incomplete_in_progress_jobs.union(incomplete_pending_jobs)
        .order_by(Job.processing_started, Job.scheduled_for)
        .all()
    )

    # temporarily mark them as ERROR so that they don't get picked up by future check_job_status tasks
    # if they haven't been re-processed in time.
    job_ids = []
    for job in jobs_not_complete_after_30_minutes:
        job.job_status = JOB_STATUS_ERROR
        dao_update_job(job)
        job_ids.append(str(job.id))

    if job_ids:
        current_app.logger.info("Job(s) {} have not completed.".format(job_ids))
        process_incomplete_jobs.apply_async([job_ids], queue=QueueNames.JOBS)


@notify_celery.task(name="replay-created-notifications")
def replay_created_notifications():
    # if the notification has not be send after 1 hour, then try to resend.
    resend_created_notifications_older_than = 60 * 60
    for notification_type in (EMAIL_TYPE, SMS_TYPE):
        notifications_to_resend = notifications_not_yet_sent(
            resend_created_notifications_older_than, notification_type
        )

        if len(notifications_to_resend) > 0:
            current_app.logger.info(
                "Sending {} {} notifications "
                "to the delivery queue because the notification "
                "status was created.".format(
                    len(notifications_to_resend), notification_type
                )
            )

        for n in notifications_to_resend:
            send_notification_to_queue(notification=n)


@notify_celery.task(name="check-for-missing-rows-in-completed-jobs")
def check_for_missing_rows_in_completed_jobs():
    jobs = find_jobs_with_missing_rows()
    for job in jobs:
        (
            recipient_csv,
            template,
            sender_id,
        ) = get_recipient_csv_and_template_and_sender_id(job)
        missing_rows = find_missing_row_for_job(job.id, job.notification_count)
        for row_to_process in missing_rows:
            row = recipient_csv[row_to_process.missing_row]
            current_app.logger.info(
                "Processing missing row: {} for job: {}".format(
                    row_to_process.missing_row, job.id
                )
            )
            process_row(row, template, job, job.service, sender_id=sender_id)


@notify_celery.task(
    name="check-for-services-with-high-failure-rates-or-sending-to-tv-numbers"
)
def check_for_services_with_high_failure_rates_or_sending_to_tv_numbers():
    start_date = datetime.utcnow() - timedelta(days=1)
    end_date = datetime.utcnow()
    message = ""

    services_with_failures = dao_find_services_with_high_failure_rates(
        start_date=start_date, end_date=end_date
    )
    services_sending_to_tv_numbers = dao_find_services_sending_to_tv_numbers(
        start_date=start_date, end_date=end_date
    )

    if services_with_failures:
        message += "{} service(s) have had high permanent-failure rates for sms messages in last 24 hours:\n".format(
            len(services_with_failures)
        )
        for service in services_with_failures:
            service_dashboard = "{}/services/{}".format(
                current_app.config["ADMIN_BASE_URL"],
                str(service.service_id),
            )
            message += "service: {} failure rate: {},\n".format(
                service_dashboard, service.permanent_failure_rate
            )
    elif services_sending_to_tv_numbers:
        message += "{} service(s) have sent over 500 sms messages to tv numbers in last 24 hours:\n".format(
            len(services_sending_to_tv_numbers)
        )
        for service in services_sending_to_tv_numbers:
            service_dashboard = "{}/services/{}".format(
                current_app.config["ADMIN_BASE_URL"],
                str(service.service_id),
            )
            message += "service: {} count of sms to tv numbers: {},\n".format(
                service_dashboard, service.notification_count
            )

    if services_with_failures or services_sending_to_tv_numbers:
        current_app.logger.warning(message)

        if current_app.config["NOTIFY_ENVIRONMENT"] in ["live", "production", "test"]:
            message += (
                "\nYou can find instructions for this ticket in our manual:\n"
                "https://github.com/alphagov/notifications-manuals/wiki/Support-Runbook#Deal-with-services-with-high-failure-rates-or-sending-sms-to-tv-numbers"  # noqa
            )
            ticket = NotifySupportTicket(
                subject=f"[{current_app.config['NOTIFY_ENVIRONMENT']}] High failure rates for sms spotted for services",
                message=message,
                ticket_type=NotifySupportTicket.TYPE_INCIDENT,
                technical_ticket=True,
            )
            zendesk_client.send_ticket_to_zendesk(ticket)
