import json
from typing import Optional
from sqlalchemy.orm import Session
from app import models

def create_version_snapshot(
    db: Session,
    memo: models.Memo,
    editor_id: int,
    summary_of_changes: Optional[str] = None
) -> models.MemoVersion:
    """
    Creates an immutable version snapshot of the memo's current title, body, and metadata.
    """
    # Count existing versions to determine next version number
    version_count = db.query(models.MemoVersion).filter(models.MemoVersion.memo_id == memo.id).count()
    version_num = version_count + 1
    
    snapshot_data = {
        "title": memo.title,
        "body": memo.body,
        "priority": memo.priority,
        "category_id": memo.category_id,
        "department_id": memo.department_id,
        "status": memo.status,
        "attachments": [
            {
                "file_name": att.file_name,
                "original_name": att.original_name,
                "file_size": att.file_size,
                "file_type": att.file_type
            }
            for att in memo.attachments
        ]
    }
    
    version = models.MemoVersion(
        memo_id=memo.id,
        version_number=version_num,
        author_id=editor_id,
        title=memo.title,
        body=memo.body,
        summary_of_changes=summary_of_changes,
        snapshot_json=json.dumps(snapshot_data)
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version
