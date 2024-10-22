import json

import pytest
from botocore.exceptions import ClientError
from celery.exceptions import MaxRetriesExceededError

import app
from app.celery import provider_tasks
from app.celery.provider_tasks import (
    check_sms_delivery_receipt,
    deliver_email,
    deliver_sms,
)
from app.clients.email import EmailClientNonRetryableException
from app.clients.email.aws_ses import (
    AwsSesClientException,
    AwsSesClientThrottlingSendRateException,
)
from app.clients.sms import SmsClientResponseException
from app.enums import NotificationStatus
from app.exceptions import NotificationTechnicalFailureException


def test_should_have_decorated_tasks_functions():
    assert deliver_sms.__wrapped__.__name__ == "deliver_sms"
    assert deliver_email.__wrapped__.__name__ == "deliver_email"


def test_should_check_delivery_receipts_success(sample_notification, mocker):
    mocker.patch("app.delivery.send_to_providers.send_sms_to_provider")
    mocker.patch(
        "app.celery.provider_tasks.aws_cloudwatch_client.is_localstack",
        return_value=False,
    )
    mocker.patch(
        "app.celery.provider_tasks.aws_cloudwatch_client.check_sms",
        return_value=("success", "okay", "AT&T"),
    )
    mock_sanitize = mocker.patch(
        "app.celery.provider_tasks.sanitize_successful_notification_by_id"
    )
    check_sms_delivery_receipt(
        "message_id", sample_notification.id, "2024-10-20 00:00:00+0:00"
    )
    # This call should be made if the message was successfully delivered
    mock_sanitize.assert_called_once()


def test_should_check_delivery_receipts_failure(sample_notification, mocker):
    mocker.patch("app.delivery.send_to_providers.send_sms_to_provider")
    mocker.patch(
        "app.celery.provider_tasks.aws_cloudwatch_client.is_localstack",
        return_value=False,
    )
    mock_update = mocker.patch(
        "app.celery.provider_tasks.update_notification_status_by_id"
    )
    mocker.patch(
        "app.celery.provider_tasks.aws_cloudwatch_client.check_sms",
        return_value=("success", "okay", "AT&T"),
    )
    mock_sanitize = mocker.patch(
        "app.celery.provider_tasks.sanitize_successful_notification_by_id"
    )
    check_sms_delivery_receipt(
        "message_id", sample_notification.id, "2024-10-20 00:00:00+0:00"
    )
    mock_sanitize.assert_not_called()
    mock_update.assert_called_once()


def test_should_call_send_sms_to_provider_from_deliver_sms_task(
    sample_notification, mocker
):
    mocker.patch("app.delivery.send_to_providers.send_sms_to_provider")
    mocker.patch("app.celery.provider_tasks.check_sms_delivery_receipt")

    deliver_sms(sample_notification.id)
    app.delivery.send_to_providers.send_sms_to_provider.assert_called_with(
        sample_notification
    )


def test_should_add_to_retry_queue_if_notification_not_found_in_deliver_sms_task(
    notify_db_session, mocker
):
    mocker.patch("app.delivery.send_to_providers.send_sms_to_provider")
    mocker.patch("app.celery.provider_tasks.deliver_sms.retry")

    notification_id = app.create_uuid()

    deliver_sms(notification_id)
    app.delivery.send_to_providers.send_sms_to_provider.assert_not_called()
    app.celery.provider_tasks.deliver_sms.retry.assert_called_with(
        queue="retry-tasks", countdown=0
    )


def test_should_retry_and_log_warning_if_SmsClientResponseException_for_deliver_sms_task(
    sample_notification, mocker
):
    mocker.patch(
        "app.delivery.send_to_providers.send_sms_to_provider",
        side_effect=SmsClientResponseException("something went wrong"),
    )
    mocker.patch("app.celery.provider_tasks.deliver_sms.retry")
    mock_logger_warning = mocker.patch("app.celery.tasks.current_app.logger.warning")
    assert sample_notification.status == NotificationStatus.CREATED

    deliver_sms(sample_notification.id)

    assert provider_tasks.deliver_sms.retry.called is True
    assert mock_logger_warning.called


def test_should_retry_and_log_exception_for_non_SmsClientResponseException_exceptions_for_deliver_sms_task(
    sample_notification, mocker
):
    mocker.patch(
        "app.delivery.send_to_providers.send_sms_to_provider",
        side_effect=Exception("something went wrong"),
    )
    mocker.patch("app.celery.provider_tasks.deliver_sms.retry")
    mock_logger_exception = mocker.patch(
        "app.celery.tasks.current_app.logger.exception"
    )

    assert sample_notification.status == NotificationStatus.CREATED
    deliver_sms(sample_notification.id)

    assert provider_tasks.deliver_sms.retry.called is True
    assert mock_logger_exception.called


def test_should_go_into_technical_error_if_exceeds_retries_on_deliver_sms_task(
    sample_notification, mocker
):
    mocker.patch(
        "app.delivery.send_to_providers.send_sms_to_provider",
        side_effect=Exception("EXPECTED"),
    )
    mocker.patch(
        "app.celery.provider_tasks.deliver_sms.retry",
        side_effect=MaxRetriesExceededError(),
    )
    mock_logger_exception = mocker.patch(
        "app.celery.tasks.current_app.logger.exception"
    )

    with pytest.raises(NotificationTechnicalFailureException) as e:
        deliver_sms(sample_notification.id)
    assert str(sample_notification.id) in str(e.value)

    provider_tasks.deliver_sms.retry.assert_called_with(
        queue="retry-tasks", countdown=0
    )

    assert sample_notification.status == NotificationStatus.TEMPORARY_FAILURE
    assert mock_logger_exception.called


# end of deliver_sms task tests, now deliver_email task tests


def test_should_call_send_email_to_provider_from_deliver_email_task(
    sample_notification, mocker
):
    mocker.patch("app.delivery.send_to_providers.send_email_to_provider")
    mocker.patch("app.redis_store.get", return_value=json.dumps({}))
    deliver_email(sample_notification.id)
    app.delivery.send_to_providers.send_email_to_provider.assert_called_with(
        sample_notification
    )


def test_should_add_to_retry_queue_if_notification_not_found_in_deliver_email_task(
    mocker,
):
    mocker.patch("app.delivery.send_to_providers.send_email_to_provider")
    mocker.patch("app.celery.provider_tasks.deliver_email.retry")

    notification_id = app.create_uuid()

    deliver_email(notification_id)
    app.delivery.send_to_providers.send_email_to_provider.assert_not_called()
    app.celery.provider_tasks.deliver_email.retry.assert_called_with(
        queue="retry-tasks"
    )


@pytest.mark.parametrize(
    "exception_class",
    [
        Exception(),
        AwsSesClientException(),
        AwsSesClientThrottlingSendRateException(),
    ],
)
def test_should_go_into_technical_error_if_exceeds_retries_on_deliver_email_task(
    sample_notification, mocker, exception_class
):
    mocker.patch(
        "app.delivery.send_to_providers.send_email_to_provider",
        side_effect=exception_class,
    )
    mocker.patch(
        "app.celery.provider_tasks.deliver_email.retry",
        side_effect=MaxRetriesExceededError(),
    )

    with pytest.raises(NotificationTechnicalFailureException) as e:
        deliver_email(sample_notification.id)
    assert str(sample_notification.id) in str(e.value)

    provider_tasks.deliver_email.retry.assert_called_with(queue="retry-tasks")
    assert sample_notification.status == NotificationStatus.TECHNICAL_FAILURE


def test_should_technical_error_and_not_retry_if_EmailClientNonRetryableException(
    sample_notification, mocker
):
    mocker.patch(
        "app.delivery.send_to_providers.send_email_to_provider",
        side_effect=EmailClientNonRetryableException("bad email"),
    )
    mocker.patch("app.redis_store.get", return_value=json.dumps({}))
    mocker.patch("app.celery.provider_tasks.deliver_email.retry")

    deliver_email(sample_notification.id)

    assert provider_tasks.deliver_email.retry.called is False
    assert sample_notification.status == NotificationStatus.TECHNICAL_FAILURE


def test_should_retry_and_log_exception_for_deliver_email_task(
    sample_notification, mocker
):
    error_response = {
        "Error": {
            "Code": "SomeError",
            "Message": "some error message from amazon",
            "Type": "Sender",
        }
    }
    ex = ClientError(error_response=error_response, operation_name="opname")
    mocker.patch(
        "app.delivery.send_to_providers.send_email_to_provider",
        side_effect=AwsSesClientException(str(ex)),
    )

    mocker.patch("app.celery.provider_tasks.deliver_email.retry")
    mock_logger_exception = mocker.patch(
        "app.celery.tasks.current_app.logger.exception"
    )

    deliver_email(sample_notification.id)

    assert provider_tasks.deliver_email.retry.called is True
    assert sample_notification.status == NotificationStatus.CREATED
    assert mock_logger_exception.called


def test_if_ses_send_rate_throttle_then_should_retry_and_log_warning(
    sample_notification, mocker
):
    error_response = {
        "Error": {
            "Code": "Throttling",
            "Message": "Maximum sending rate exceeded.",
            "Type": "Sender",
        }
    }
    ex = ClientError(error_response=error_response, operation_name="opname")
    mocker.patch("app.redis_store.get", return_value=json.dumps({}))
    mocker.patch(
        "app.delivery.send_to_providers.send_email_to_provider",
        side_effect=AwsSesClientThrottlingSendRateException(str(ex)),
    )
    mocker.patch("app.celery.provider_tasks.deliver_email.retry")
    mock_logger_warning = mocker.patch("app.celery.tasks.current_app.logger.warning")
    mock_logger_exception = mocker.patch(
        "app.celery.tasks.current_app.logger.exception"
    )

    deliver_email(sample_notification.id)

    assert provider_tasks.deliver_email.retry.called is True
    assert sample_notification.status == NotificationStatus.CREATED
    assert not mock_logger_exception.called
    assert mock_logger_warning.called
