from app.db.legal_documents import build_legal_document
from app.db.resource_documents import build_resource_document
from app.repositories.resource_repository import (
    create_legal_document,
    create_resource,
    get_legal_documents_by_category,
    get_resources_by_category,
)


async def add_legal_document(
    title: str,
    category: str,
    source: str,
    description: str | None = None,
    document_type: str = "legal_reference",
    version: str | None = None,
):
    document = build_legal_document(
        title=title,
        category=category,
        source=source,
        description=description,
        document_type=document_type,
        version=version,
    )

    return await create_legal_document(document)


async def list_legal_documents(
    category: str,
):
    return await get_legal_documents_by_category(category)


async def add_resource(
    title: str,
    category: str,
    description: str,
    url: str | None = None,
    organization: str | None = None,
):
    resource = build_resource_document(
        title=title,
        category=category,
        description=description,
        url=url,
        organization=organization,
    )

    return await create_resource(resource)


async def list_resources(
    category: str,
):
    return await get_resources_by_category(category)