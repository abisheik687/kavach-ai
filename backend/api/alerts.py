"""
KAVACH-AI Alerts API
Manage threat alerts and forensic evidence
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from datetime import datetime
from loguru import logger

from backend.database import get_db, Alert, EvidenceChain
from backend.schemas import AlertResponse, AlertAcknowledge, EvidenceChainResponse
from backend.config import settings

router = APIRouter()


@router.get("/", response_model=List[AlertResponse])
async def query_alerts(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    attack_type: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Query alert history with filters.
    
    Filters:
    - status: unacknowledged, acknowledged, resolved, false_positive
    - severity: low, medium, high, critical, emergency
    - attack_type: Attack classification
    - start_time / end_time: Time range (UTC)
    - limit / offset: Pagination
    """
    try:
        query = db.query(Alert)
        
        # Apply filters
        filters = []
        
        if status:
            filters.append(Alert.status == status)
        
        if severity:
            filters.append(Alert.severity == severity)
        
        if attack_type:
            filters.append(Alert.attack_type == attack_type)
        
        if start_time:
            filters.append(Alert.created_at >= start_time)
        
        if end_time:
            filters.append(Alert.created_at <= end_time)
        
        if filters:
            query = query.filter(and_(*filters))
        
        # Order and paginate
        alerts = query.order_by(
            Alert.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        return alerts
    
    except Exception as e:
        logger.error(f"Error querying alerts: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error querying alerts: {str(e)}"
        )


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific alert"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(
            status_code=404,
            detail=f"Alert {alert_id} not found"
        )
    
    return alert


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: int,
    ack: AlertAcknowledge,
    db: Session = Depends(get_db)
):
    """
    Acknowledge an alert.
    
    This marks the alert as acknowledged and records who acknowledged it.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(
            status_code=404,
            detail=f"Alert {alert_id} not found"
        )
    
    try:
        alert.status = "acknowledged"
        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledged_by = ack.acknowledged_by
        
        # Add notes to context if provided
        if ack.notes:
            if not alert.context_json:
                alert.context_json = {}
            alert.context_json["acknowledgment_notes"] = ack.notes
        
        db.commit()
        db.refresh(alert)
        
        logger.info(f"Alert {alert_id} acknowledged by {ack.acknowledged_by}")
        
        return alert
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error acknowledging alert: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error acknowledging alert: {str(e)}"
        )


@router.get("/{alert_id}/evidence", response_model=List[EvidenceChainResponse])
async def get_alert_evidence(
    alert_id: int,
    db: Session = Depends(get_db)
):
    """
    Get forensic evidence chain for an alert.
    
    Returns the complete Merkle tree evidence chain with cryptographic hashes.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(
            status_code=404,
            detail=f"Alert {alert_id} not found"
        )
    
    # Get evidence chain
    evidence_chain = db.query(EvidenceChain).filter(
        EvidenceChain.alert_id == alert_id
    ).order_by(EvidenceChain.timestamp).all()
    
    return evidence_chain

import json
import datetime
from fastapi.responses import Response
from backend.models import ScanResult, EvidenceChain

@router.get("/{alert_id}/evidence/export", response_class=Response)
async def export_alert_evidence(
    alert_id: int,
    db: Session = Depends(get_db)
) -> Response:
    """
    Build and return a downloadable evidence bundle for the given alert.
    The bundle contains: alert metadata, scan result scores per model,
    GradCAM path, and the full evidence chain log.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "alert_not_found",
                    "message": f"No alert found with id={alert_id}"},
        )

    scan = db.query(ScanResult).filter(
        ScanResult.alert_id == alert_id
    ).first()

    chain_entries = db.query(EvidenceChain).filter(
        EvidenceChain.alert_id == alert_id
    ).order_by(EvidenceChain.timestamp.asc()).all()

    model_scores: dict = {}
    if scan and scan.model_scores:
        try:
            model_scores = json.loads(scan.model_scores)
        except (TypeError, json.JSONDecodeError):
            model_scores = {}

    bundle = {
        "schema_version": "1.0",
        "exported_at": datetime.datetime.utcnow().isoformat() + "Z",
        "alert": {
            "id": alert.id,
            "created_at": alert.created_at.isoformat() if alert.created_at else None,
            "severity": alert.severity,
            "source_type": alert.source_type,
            "source_url": getattr(alert, 'source_url', None),
        },
        "verdict": {
            "label": scan.verdict if scan else "unknown",
            "confidence": scan.confidence if scan else None,
            "faces_detected": scan.faces_detected if scan else 0,
            "processing_time_ms": scan.processing_time_ms if scan else None,
        },
        "model_scores": model_scores,
        "explainability": {
            "gradcam_path": scan.gradcam_path if scan else None,
            "gradcam_available": bool(scan and scan.gradcam_path),
        },
        "evidence_chain": [
            {
                "step": i + 1,
                "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
                "stage": getattr(entry, 'stage', str(entry.id)),
                "detail": getattr(entry, 'detail', str(entry.id)),
                "model": getattr(entry, 'model_name', None),
                "score": getattr(entry, 'score', None),
            }
            for i, entry in enumerate(chain_entries)
        ],
    }

    payload = json.dumps(bundle, indent=2, default=str)
    filename = f"kavach_evidence_alert_{alert_id}.json"

    return Response(
        content=payload,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Evidence-Alert-ID": str(alert_id),
            "X-Export-Timestamp": bundle["exported_at"],
        },
    )
@router.post("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: int,
    resolution_notes: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Mark an alert as resolved.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(
            status_code=404,
            detail=f"Alert {alert_id} not found"
        )
    
    try:
        alert.status = "resolved"
        alert.end_time = datetime.utcnow()
        
        if resolution_notes:
            if not alert.context_json:
                alert.context_json = {}
            alert.context_json["resolution_notes"] = resolution_notes
        
        db.commit()
        db.refresh(alert)
        
        logger.info(f"Alert {alert_id} resolved")
        
        return alert
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error resolving alert: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error resolving alert: {str(e)}"
        )


@router.post("/{alert_id}/false-positive", response_model=AlertResponse)
async def mark_false_positive(
    alert_id: int,
    notes: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Mark an alert as a false positive.
    
    This is important for model improvement and calibration.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(
            status_code=404,
            detail=f"Alert {alert_id} not found"
        )
    
    try:
        alert.status = "false_positive"
        alert.end_time = datetime.utcnow()
        
        if notes:
            if not alert.context_json:
                alert.context_json = {}
            alert.context_json["false_positive_notes"] = notes
        
        db.commit()
        db.refresh(alert)
        
        logger.info(f"Alert {alert_id} marked as false positive")
        
        # TODO: Use this feedback for model calibration
        
        return alert
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error marking false positive: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error marking false positive: {str(e)}"
        )
