from app.db.audit_documents import build_audit_log_document
from app.repositories.audit_repository import (
    create_audit_log,
    get_user_audit_logs,
)


async def record_audit_event(
    action: str,
    user_id=None,
    resource_type: str | None = None,
    resource_id=None,
    details: dict | None = None,
):
    audit_data = build_audit_log_document(
        action=action,
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
    )

    return await create_audit_log(audit_data)


async def list_user_audit_logs(user_id):
    return await get_user_audit_logs(user_id)