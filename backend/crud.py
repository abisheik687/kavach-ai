from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
from backend.database import User, ScanResult, AuditLog
from backend.api.auth import get_password_hash

# KAVACH-AI Day 11: Database CRUD
# Encapsulates DB access logic

async def create_scan_result(db: AsyncSession, task_id: str, filename: str, owner_id: int):
    db_scan = ScanResult(
        task_id=task_id,
        filename=filename,
        owner_id=owner_id,
        status="queued",
        created_at=datetime.utcnow()
    )
    db.add(db_scan)
    await db.commit()
    await db.refresh(db_scan)
    return db_scan

async def update_scan_result(db: AsyncSession, task_id: str, report: dict, status="completed"):
    result = await db.execute(select(ScanResult).filter(ScanResult.task_id == task_id))
    db_scan = result.scalars().first()
    if db_scan:
        db_scan.status = status
        db_scan.final_score = report.get("final_score")
        db_scan.verdict = report.get("verdict")
        db_scan.confidence = report.get("confidence")
        
        # Parse breakdown if available
        breakdown = report.get("breakdown", {})
        db_scan.video_score = breakdown.get("video_spatial")
        db_scan.audio_score = breakdown.get("audio_spectral")
        db_scan.temporal_score = breakdown.get("temporal_lstm")
        
        db_scan.completed_at = datetime.utcnow()
        await db.commit()
        await db.refresh(db_scan)
    return db_scan

async def log_action(db: AsyncSession, user_id: int, action: str, details: str):
    log = AuditLog(
        user_id=user_id,
        action=action,
        user=str(user_id) # For backward compatibility with 'user' column
    )
    log.details_json = {"message": details} 
    
    db.add(log)
    await db.commit()
    return log

async def get_scan_result(db: AsyncSession, task_id: str):
    result = await db.execute(select(ScanResult).filter(ScanResult.task_id == task_id))
    return result.scalars().first()

async def get_user_scans(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100):
    result = await db.execute(
        select(ScanResult)
        .filter(ScanResult.owner_id == user_id)
        .order_by(ScanResult.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()
