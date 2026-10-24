

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from ..audit.service import record_audit_event
from ..database import get_db
from ..models import Document, DocumentPermission, User
from ..auth.dependencies import get_current_user

router = APIRouter(prefix="/documents", tags=["Documents"])

class ShareDocumentRequest(BaseModel):
    email: EmailStr
    can_read: bool = True
    can_edit: bool = False


class UpdateDocumentRequest(BaseModel):
    category: str = Field(min_length=1, max_length=100)

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 5 * 1024 * 1024

ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "image/png": ".png",
    "image/jpeg": ".jpg",
}


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    category: str = "General",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content_type = file.content_type or ""
    if content_type not in ALLOWED_TYPES:
        record_audit_event(
            db,
            actor_id=current_user.id,
            action="document_upload",
            resource_type="document",
            outcome="denied",
            details="Rejected unsupported content type",
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type",
        )

    original_name = Path(file.filename or "document").name
    if not original_name.strip():
        raise HTTPException(
            status_code=400,
            detail="Invalid filename",
        )

    contents = await file.read(MAX_FILE_SIZE + 1)
    if len(contents) > MAX_FILE_SIZE:
        record_audit_event(
            db,
            actor_id=current_user.id,
            action="document_upload",
            resource_type="document",
            outcome="denied",
            details="Rejected file exceeding size limit",
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Maximum file size is 5 MB",
        )

    # Do not trust the client-supplied MIME type alone.
    signatures = {
        "application/pdf": b"%PDF-",
        "image/png": b"\x89PNG\r\n\x1a\n",
        "image/jpeg": b"\xff\xd8\xff",
    }
    expected_signature = signatures.get(content_type)
    if expected_signature and not contents.startswith(expected_signature):
        record_audit_event(
            db,
            actor_id=current_user.id,
            action="document_upload",
            resource_type="document",
            outcome="denied",
            details="File signature did not match declared type",
        )
        db.commit()
        raise HTTPException(
            status_code=400,
            detail="File content does not match the declared type",
        )

    stored_name = f"{uuid.uuid4().hex}{ALLOWED_TYPES[content_type]}"
    destination = UPLOAD_DIR / stored_name

    document = Document(
        original_filename=original_name[:255],
        stored_filename=stored_name,
        category=category.strip()[:100] or "General",
        content_type=content_type,
        size_bytes=len(contents),
        owner_id=current_user.id,
    )

    try:
        with destination.open("xb") as output:
            output.write(contents)

        db.add(document)
        db.flush()

        record_audit_event(
            db,
            actor_id=current_user.id,
            action="document_upload",
            resource_type="document",
            resource_id=str(document.id),
            outcome="success",
            details=f"Uploaded {document.original_filename}; {len(contents)} bytes",
        )
        db.commit()
        db.refresh(document)
    except Exception:
        db.rollback()
        if destination.exists():
            destination.unlink()
        raise HTTPException(
            status_code=500,
            detail="Document upload failed",
        ) from None

    return {
        "id": document.id,
        "filename": document.original_filename,
        "category": document.category,
        "size_bytes": document.size_bytes,
        "owner_id": document.owner_id,
        "created_at": document.created_at,
    }


@router.get("")
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    documents = db.execute(
        select(Document, DocumentPermission)
        .outerjoin(
            DocumentPermission,
            and_(
                DocumentPermission.document_id == Document.id,
                DocumentPermission.user_id == current_user.id,
            ),
        )
        .where(
            or_(
                Document.owner_id == current_user.id,
                and_(
                    DocumentPermission.user_id == current_user.id,
                    DocumentPermission.can_read.is_(True),
                ),
            )
        )
        .order_by(Document.created_at.desc())
    ).all()

    return [
        {
            "id": doc.id,
            "filename": doc.original_filename,
            "category": doc.category,
            "size_bytes": doc.size_bytes,
            "owner_id": doc.owner_id,
            "created_at": doc.created_at,
            "access": (
                "owner"
                if doc.owner_id == current_user.id
                else "shared"
            ),
            "can_read": (
                True
                if doc.owner_id == current_user.id
                else permission.can_read
            ),
            "can_edit": (
                True
                if doc.owner_id == current_user.id
                else permission.can_edit
            ),
        }
        for doc, permission in documents
    ]


@router.patch("/{document_id}")
def update_document(
    document_id: int,
    request: UpdateDocumentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.get(Document, document_id)

    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    allowed = document.owner_id == current_user.id

    if not allowed:
        permission = db.scalar(
            select(DocumentPermission).where(
                DocumentPermission.document_id == document_id,
                DocumentPermission.user_id == current_user.id,
            )
        )
        allowed = permission is not None and permission.can_edit

    if not allowed:
        record_audit_event(
            db,
            actor_id=current_user.id,
            action="document_edit",
            resource_type="document",
            resource_id=str(document_id),
            outcome="denied",
            details="User does not have edit permission",
        )
        db.commit()
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to edit this document",
        )

    category = request.category.strip()
    if not category:
        raise HTTPException(
            status_code=422,
            detail="Category must not be blank",
        )

    document.category = category

    record_audit_event(
        db,
        actor_id=current_user.id,
        action="document_edit",
        resource_type="document",
        resource_id=str(document_id),
        outcome="success",
        details="Document category updated",
    )
    db.commit()
    db.refresh(document)

    return {
        "id": document.id,
        "category": document.category,
        "updated_at": document.updated_at.isoformat(),
    }


@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.get(Document, document_id)

    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    allowed = document.owner_id == current_user.id

    if not allowed:
        permission = db.scalar(
            select(DocumentPermission).where(
                DocumentPermission.document_id == document_id,
                DocumentPermission.user_id == current_user.id,
            )
        )
        allowed = permission is not None and permission.can_read

    if not allowed:
        record_audit_event(
            db,
            actor_id=current_user.id,
            action="document_download",
            resource_type="document",
            resource_id=str(document_id),
            outcome="denied",
            details="User does not have read permission",
        )
        db.commit()
        raise HTTPException(status_code=403, detail="You do not have permission to download this document")

    file_path = UPLOAD_DIR / document.stored_filename

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Stored file not found")

    record_audit_event(
        db,
        actor_id=current_user.id,
        action="document_download",
        resource_type="document",
        resource_id=str(document_id),
        outcome="success",
        details="Document download authorized",
    )
    db.commit()

    return FileResponse(
        path=file_path,
        media_type=document.content_type,
        filename=document.original_filename,
    )


@router.post("/{document_id}/share")
def share_document(
    document_id: int,
    request: ShareDocumentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.get(Document, document_id)

    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.owner_id != current_user.id:
        record_audit_event(
            db,
            actor_id=current_user.id,
            action="document_share",
            resource_type="document",
            resource_id=str(document_id),
            outcome="denied",
            details="Only the document owner can grant access",
        )
        db.commit()
        raise HTTPException(status_code=403, detail="Only the owner can share this document")

    target = db.scalar(
        select(User).where(User.email == str(request.email).lower())
    )

    if target is None or not target.is_active:
        raise HTTPException(status_code=404, detail="Active recipient not found")

    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot share a document with yourself")

    permission = db.scalar(
        select(DocumentPermission).where(
            DocumentPermission.document_id == document_id,
            DocumentPermission.user_id == target.id,
        )
    )

    # Editing access always includes reading access.
    can_read = request.can_read or request.can_edit

    if permission is None:
        permission = DocumentPermission(
            document_id=document_id,
            user_id=target.id,
            can_read=can_read,
            can_edit=request.can_edit,
            granted_by=current_user.id,
        )
        db.add(permission)
    else:
        permission.can_read = can_read
        permission.can_edit = request.can_edit
        permission.granted_by = current_user.id

    record_audit_event(
        db,
        actor_id=current_user.id,
        action="document_share",
        resource_type="document",
        resource_id=str(document_id),
        outcome="success",
        details=f"Access granted to user {target.id}; read={can_read}, edit={request.can_edit}",
    )

    db.commit()

    return {
        "message": "Document permissions updated",
        "document_id": document_id,
        "user_id": target.id,
        "can_read": can_read,
        "can_edit": request.can_edit,
    }


@router.delete("/{document_id}/share/{user_id}")
def revoke_document_access(
    document_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.get(Document, document_id)

    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.owner_id != current_user.id:
        record_audit_event(
            db,
            actor_id=current_user.id,
            action="document_access_revoke",
            resource_type="document",
            resource_id=str(document_id),
            outcome="denied",
            details="Only the owner can revoke access",
        )
        db.commit()
        raise HTTPException(status_code=403, detail="Only the owner can revoke access")

    permission = db.scalar(
        select(DocumentPermission).where(
            DocumentPermission.document_id == document_id,
            DocumentPermission.user_id == user_id,
        )
    )

    if permission is None:
        raise HTTPException(status_code=404, detail="Permission not found")

    db.delete(permission)

    record_audit_event(
        db,
        actor_id=current_user.id,
        action="document_access_revoke",
        resource_type="document",
        resource_id=str(document_id),
        outcome="success",
        details=f"Access revoked for user {user_id}",
    )

    db.commit()

    return {"message": "Document access revoked", "document_id": document_id, "user_id": user_id}
