from pathlib import Path

from fastapi import UploadFile

from app.schemas import RequirementUploadResponse


async def store_requirement(
    file: UploadFile,
    upload_dir: str,
    owner: str,
) -> RequirementUploadResponse:
    target = Path(upload_dir) / str(file.filename)
    content = await file.read()
    target.write_bytes(content)
    return RequirementUploadResponse(
        owner=owner,
        fileName=file.filename,
        storedAt=str(target),
        size=len(content),
    )