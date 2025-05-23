from sqlalchemy import delete, select

from app import db
from app.dao.dao_utils import autocommit
from app.models import ServicePermission


def dao_fetch_service_permissions(service_id):

    stmt = select(ServicePermission).where(ServicePermission.service_id == service_id)
    return db.session.execute(stmt).scalars().all()


@autocommit
def dao_add_service_permission(service_id, permission):
    service_permission = ServicePermission(service_id=service_id, permission=permission)
    db.session.add(service_permission)


def dao_remove_service_permission(service_id, permission):

    stmt = delete(ServicePermission).where(
        ServicePermission.service_id == service_id,
        ServicePermission.permission == permission,
    )
    result = db.session.execute(stmt)
    db.session.commit()
    return result.rowcount
