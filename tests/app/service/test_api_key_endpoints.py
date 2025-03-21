import json

from flask import url_for
from sqlalchemy import func, select

from app import db
from app.dao.api_key_dao import expire_api_key
from app.enums import KeyType
from app.models import ApiKey
from tests import create_admin_authorization_header
from tests.app.db import create_api_key, create_service, create_user


def test_api_key_should_create_new_api_key_for_service(notify_api, sample_service):
    with notify_api.test_request_context():
        with notify_api.test_client() as client:
            data = {
                "name": "some secret name",
                "created_by": str(sample_service.created_by.id),
                "key_type": KeyType.NORMAL,
            }
            auth_header = create_admin_authorization_header()
            response = client.post(
                url_for("service.create_api_key", service_id=sample_service.id),
                data=json.dumps(data),
                headers=[("Content-Type", "application/json"), auth_header],
            )
            assert response.status_code == 201
            assert "data" in json.loads(response.get_data(as_text=True))
            saved_api_key = (
                db.session.execute(
                    select(ApiKey).where(ApiKey.service_id == sample_service.id)
                )
                .scalars()
                .first()
            )
            assert saved_api_key.service_id == sample_service.id
            assert saved_api_key.name == "some secret name"


def test_api_key_should_return_error_when_service_does_not_exist(
    notify_api, sample_service
):
    with notify_api.test_request_context():
        with notify_api.test_client() as client:
            import uuid

            missing_service_id = uuid.uuid4()
            auth_header = create_admin_authorization_header()
            response = client.post(
                url_for("service.create_api_key", service_id=missing_service_id),
                headers=[("Content-Type", "application/json"), auth_header],
            )
            assert response.status_code == 404


def test_create_api_key_without_key_type_rejects(client, sample_service):
    data = {"name": "some secret name", "created_by": str(sample_service.created_by.id)}
    auth_header = create_admin_authorization_header()
    response = client.post(
        url_for("service.create_api_key", service_id=sample_service.id),
        data=json.dumps(data),
        headers=[("Content-Type", "application/json"), auth_header],
    )
    assert response.status_code == 400
    json_resp = json.loads(response.get_data(as_text=True))
    assert json_resp["result"] == "error"
    assert json_resp["message"] == {"key_type": ["Missing data for required field."]}


def _get_api_key_count():
    stmt = select(func.count()).select_from(ApiKey)
    return db.session.execute(stmt).scalar() or 0


def test_revoke_should_expire_api_key_for_service(notify_api, sample_api_key):
    with notify_api.test_request_context():
        with notify_api.test_client() as client:
            assert _get_api_key_count() == 1
            auth_header = create_admin_authorization_header()
            response = client.post(
                url_for(
                    "service.revoke_api_key",
                    service_id=sample_api_key.service_id,
                    api_key_id=sample_api_key.id,
                ),
                headers=[auth_header],
            )
            assert response.status_code == 202
            api_keys_for_service = db.session.get(ApiKey, sample_api_key.id)
            assert api_keys_for_service.expiry_date is not None


def test_api_key_should_create_multiple_new_api_key_for_service(
    notify_api, sample_service
):
    with notify_api.test_request_context():
        with notify_api.test_client() as client:
            assert _get_api_key_count() == 0
            data = {
                "name": "some secret name",
                "created_by": str(sample_service.created_by.id),
                "key_type": KeyType.NORMAL,
            }
            auth_header = create_admin_authorization_header()
            response = client.post(
                url_for("service.create_api_key", service_id=sample_service.id),
                data=json.dumps(data),
                headers=[("Content-Type", "application/json"), auth_header],
            )
            assert response.status_code == 201
            assert _get_api_key_count() == 1

            data["name"] = "another secret name"
            auth_header = create_admin_authorization_header()
            response2 = client.post(
                url_for("service.create_api_key", service_id=sample_service.id),
                data=json.dumps(data),
                headers=[("Content-Type", "application/json"), auth_header],
            )
            assert response2.status_code == 201
            assert json.loads(response.get_data(as_text=True)) != json.loads(
                response2.get_data(as_text=True)
            )
            assert _get_api_key_count() == 2


def test_get_api_keys_should_return_all_keys_for_service(notify_api, sample_api_key):
    with notify_api.test_request_context():
        with notify_api.test_client() as client:
            another_user = create_user(email="another@it.gov.uk")

            another_service = create_service(
                user=another_user, service_name="Another service"
            )
            # key for another service
            create_api_key(another_service)

            # this service already has one key, add two more, one expired
            create_api_key(sample_api_key.service)
            one_to_expire = create_api_key(sample_api_key.service)
            expire_api_key(
                service_id=one_to_expire.service_id, api_key_id=one_to_expire.id
            )

            assert _get_api_key_count() == 4

            auth_header = create_admin_authorization_header()
            response = client.get(
                url_for("service.get_api_keys", service_id=sample_api_key.service_id),
                headers=[("Content-Type", "application/json"), auth_header],
            )
            assert response.status_code == 200
            json_resp = json.loads(response.get_data(as_text=True))
            assert len(json_resp["apiKeys"]) == 3


def test_get_api_keys_should_return_one_key_for_service(notify_api, sample_api_key):
    with notify_api.test_request_context():
        with notify_api.test_client() as client:
            auth_header = create_admin_authorization_header()
            response = client.get(
                url_for(
                    "service.get_api_keys",
                    service_id=sample_api_key.service_id,
                    key_id=sample_api_key.id,
                ),
                headers=[("Content-Type", "application/json"), auth_header],
            )
            assert response.status_code == 200
            json_resp = json.loads(response.get_data(as_text=True))
            assert len(json_resp["apiKeys"]) == 1
