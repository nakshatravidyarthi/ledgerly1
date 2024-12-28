from fastapi import APIRouter, HTTPException, UploadFile, Form
from typing import List
from app.db.models import receipts
from app.routers.deps import SessionDep
from app.core.config import settings
import boto3
from botocore.exceptions import NoCredentialsError
from uuid import uuid4
from sqlmodel import select

router = APIRouter(prefix="/receipts", tags=["Receipts"])

@router.post("/upload", summary="Upload receipt to S3 and store metadata")
def upload_receipt(file: UploadFile, user_id: str = Form(...), category: str = Form(...)):
    if category not in ["food", "entertainment", "work"]:
        raise HTTPException(status_code=400, detail="Invalid category")

    try:
        s3_client = boto3.client("s3", region_name=settings.REGION)
        receipt_id = str(uuid4())
        key = f"{receipt_id}_{file.filename}"
        metadata = {'Metadata': {'category': category, 'user': user_id}, 'ACL': 'public-read'}

        s3_client.upload_fileobj(file.file, settings.S3_BUCKET, key, ExtraArgs=metadata)
        return {"message": "Uploaded successfully", "File": key}
    except NoCredentialsError:
        raise HTTPException(status_code=500, detail="AWS credentials not found")

@router.get("/expenses/{user_id}", summary="Get all expenses for a user", response_model=List[receipts])
def get_expenses(user_id: str, session: SessionDep):
    try:
        expenses = session.exec(
            select(receipts).where(receipts.user_id == user_id)
        ).all()
        return expenses
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching expenses: {e}")