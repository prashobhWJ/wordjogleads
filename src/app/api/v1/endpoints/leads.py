"""
Leads API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.dependencies import get_db
from app.services.lead_service import LeadService
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/leads")
async def get_leads(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get all leads from the database.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
    
    Returns:
        List of leads
    """
    try:
        service = LeadService(db)
        leads = service.get_all_leads(skip=skip, limit=limit)
        
        return {
            "total": len(leads),
            "skip": skip,
            "limit": limit,
            "leads": [
                {
                    "id": lead.id,
                    "lead_id": lead.lead_id,
                    "full_name": lead.full_name,
                    "email": lead.email,
                    "phone": lead.phone,
                    "city": lead.city,
                    "state_province": lead.state_province,
                    "employment_status": lead.employment_status,
                    "company_name": lead.company_name,
                    "created_at": lead.created_at.isoformat() if lead.created_at else None,
                }
                for lead in leads
            ]
        }
    except Exception as e:
        logger.error(f"[red]Error fetching leads:[/red] {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/leads/{lead_id}")
async def get_lead(
    lead_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific lead by lead_id.
    
    Args:
        lead_id: Lead ID (external identifier)
        db: Database session
    
    Returns:
        Lead details
    """
    try:
        service = LeadService(db)
        lead = service.get_lead_by_lead_id(lead_id)
        
        if not lead:
            raise HTTPException(status_code=404, detail=f"Lead with ID '{lead_id}' not found")
        
        return {
            "id": lead.id,
            "lead_id": lead.lead_id,
            "first_name": lead.first_name,
            "last_name": lead.last_name,
            "full_name": lead.full_name,
            "email": lead.email,
            "phone": lead.phone,
            "date_of_birth": lead.date_of_birth.isoformat() if lead.date_of_birth else None,
            "address_line1": lead.address_line1,
            "address_line2": lead.address_line2,
            "city": lead.city,
            "state_province": lead.state_province,
            "postal_code": lead.postal_code,
            "country": lead.country,
            "country_code": lead.country_code,
            "vehicle_type": lead.vehicle_type,
            "current_credit": lead.current_credit,
            "employment_status": lead.employment_status,
            "job_title": lead.job_title,
            "company_name": lead.company_name,
            "monthly_salary_min": float(lead.monthly_salary_min) if lead.monthly_salary_min else None,
            "monthly_salary_max": float(lead.monthly_salary_max) if lead.monthly_salary_max else None,
            "employment_length": lead.employment_length,
            "length_at_company": lead.length_at_company,
            "length_at_home_address": lead.length_at_home_address,
            "created_at": lead.created_at.isoformat() if lead.created_at else None,
            "updated_at": lead.updated_at.isoformat() if lead.updated_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[red]Error fetching lead {lead_id}:[/red] {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/leads/sync")
async def sync_leads_to_crm(
    skip: int = Query(0, ge=0),
    limit: Optional[int] = Query(None, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Sync all leads from database to Twenty CRM.
    
    Args:
        skip: Number of leads to skip
        limit: Maximum number of leads to sync (None for all)
        db: Database session
    
    Returns:
        Sync results with success/failure counts
    """
    try:
        service = LeadService(db)
        results = await service.sync_all_leads_to_crm(skip=skip, limit=limit)
        
        return {
            "message": "Lead sync completed",
            "results": results
        }
    except Exception as e:
        logger.error(f"[red]Error syncing leads to CRM:[/red] {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/leads/{lead_id}/sync")
async def sync_lead_to_crm(
    lead_id: str,
    db: Session = Depends(get_db)
):
    """
    Sync a single lead to Twenty CRM.
    
    Args:
        lead_id: Lead ID (external identifier)
        db: Database session
    
    Returns:
        CRM response
    """
    try:
        service = LeadService(db)
        lead = service.get_lead_by_lead_id(lead_id)
        
        if not lead:
            raise HTTPException(status_code=404, detail=f"Lead with ID '{lead_id}' not found")
        
        response = await service.sync_lead_to_crm(lead)
        
        return {
            "message": f"Lead '{lead_id}' synced successfully",
            "lead_id": lead_id,
            "crm_response": response
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[red]Error syncing lead {lead_id} to CRM:[/red] {e}")
        raise HTTPException(status_code=500, detail=str(e))
