from fastapi import APIRouter, HTTPException, UploadFile, Form, Depends
from typing import List
from app.db.models import receipts, CreateReceipt
from app.routers.deps import SessionDep
from app.core.config import settings
import boto3
from botocore.exceptions import NoCredentialsError
from uuid import uuid4
from sqlmodel import select

router = APIRouter(prefix="/receipts", tags=["Receipts"])


@router.post(
    "/uploadExpenses",
    summary="Upload receipt to S3 and store metadata",
    responses={
        201: {"description": "Successful Upload", "content": {"application/json": {"example": {"message": "Successful Upload", "File": "unique_key.jpeg"}}}},
        400: {"description": "Invalid category"},
        401: {"description": "AWS credentials not found"},
    },
)
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
        raise HTTPException(status_code=401, detail="AWS credentials not found")


@router.post(
    "/createExpenses/{user_id}",
    summary="Create new record of user's expenses",
    responses={
        201: {"description": "Successfully created expense record"},
        500: {"description": "CREATE operation error"},
    },
)
def create_expenses(session: SessionDep, user_id: str, createreceipt: CreateReceipt = Depends()):
    try:
        rid = str(uuid4())
        new_expense = receipts(
            receipt_id=rid,
            category=createreceipt.category,
            receipt_date=createreceipt.receipt_date,
            vendor_name=createreceipt.vendor_name,
            total_amount=createreceipt.total_amount,
            s3_url=None,
            user_id=user_id,
        )
        session.add(new_expense)
        session.commit()
        return {"message": "Successfully created expense record", "receipt_id": rid}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"CREATE operation error: {e}")


@router.get(
    "/getExpenses/{user_id}",
    summary="Get all expenses for a user",
    response_model=List[receipts],
    responses={
        200: {"description": "Successfully fetched list of user expense records"},
        500: {"description": "READ operation error"},
    },
)
def get_expenses(user_id: str, session: SessionDep):
    try:
        expenses = session.exec(
            select(receipts).where(receipts.user_id == user_id)
        ).all()
        return expenses
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"READ operation error: {e}")
