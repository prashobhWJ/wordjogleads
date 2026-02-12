"""
Leads API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.dependencies import get_db
from app.services.lead_service import LeadService
from app.utils.logging import get_logger
from app.schemas.leads import LeadListResponse, LeadDetail, LeadSyncResponse, SalesAgentMatchResponse

logger = get_logger(__name__)
router = APIRouter()


@router.get("/leads", response_model=LeadListResponse)
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


@router.get("/leads/{lead_id}", response_model=LeadDetail)
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


@router.post("/leads/sync", response_model=LeadSyncResponse)
async def sync_leads_to_crm(
    skip: int = Query(0, ge=0),
    limit: Optional[int] = Query(None, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Sync all leads to Twenty CRM.
    
    The lead source (database or email) is determined by the `lead_source.type` 
    setting in config.yaml:
    - If "db": Syncs leads from the database
    - If "email": Processes unread emails and extracts leads
    
    Args:
        skip: Number of leads to skip (for database source only)
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


@router.post("/leads/{lead_id}/sync", response_model=LeadSyncResponse)
async def sync_lead_to_crm(
    lead_id: str,
    match_sales_agent: bool = Query(True, description="Whether to match lead to sales agent before syncing"),
    db: Session = Depends(get_db)
):
    """
    Sync a single lead to Twenty CRM.
    Optionally matches the lead to a sales agent before syncing.
    
    Args:
        lead_id: Lead ID (external identifier)
        match_sales_agent: Whether to match lead to sales agent (default: True)
        db: Database session
    
    Returns:
        CRM response with optional sales agent match
    """
    try:
        service = LeadService(db)
        lead = service.get_lead_by_lead_id(lead_id)
        
        if not lead:
            raise HTTPException(status_code=404, detail=f"Lead with ID '{lead_id}' not found")
        
        response = await service.sync_lead_to_crm(lead, match_sales_agent=match_sales_agent)
        
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


@router.post("/leads/{lead_id}/match-agent", response_model=SalesAgentMatchResponse)
async def match_lead_to_sales_agent(
    lead_id: str,
    version: Optional[str] = Query(None, description="Prompt version to use (v1 or v2)"),
    db: Session = Depends(get_db)
):
    """
    Match a lead to the best sales agent using LLM.
    
    Args:
        lead_id: Lead ID (external identifier)
        version: Prompt version to use (defaults to configured version)
        db: Database session
    
    Returns:
        Sales agent match result with selected agent and reasoning
    """
    try:
        service = LeadService(db)
        lead = service.get_lead_by_lead_id(lead_id)
        
        if not lead:
            raise HTTPException(status_code=404, detail=f"Lead with ID '{lead_id}' not found")
        
        result = await service.match_lead_to_sales_agent(lead, version=version)
        
        return {
            "message": f"Lead '{lead_id}' matched to sales agent",
            "lead_id": lead_id,
            "selected_agent_id": result.get("selected_agent_id"),
            "selected_agent_name": result.get("selected_agent_name"),
            "confidence_score": result.get("confidence_score"),
            "reasoning": result.get("reasoning"),
            "alternative_agents": result.get("alternative_agents", []),
            "match_result": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[red]Error matching lead {lead_id} to sales agent:[/red] {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/leads/process-emails", response_model=LeadSyncResponse)
async def process_emails_to_leads(
    max_emails: int = Query(50, ge=1, le=100, description="Maximum number of emails to process"),
    match_sales_agent: bool = Query(True, description="Whether to match leads to sales agents"),
    db: Session = Depends(get_db)
):
    """
    Process recent emails (within configured time period) from Microsoft 365,
    extract lead information using LLM, and sync to CRM with reasoning notes.
    
    Only emails that arrived within the last N minutes (configured via 
    recent_email_minutes in config.yaml) will be processed.
    
    This endpoint:
    1. Reads recent unread emails from the configured mailbox (filtered by time period)
    2. Uses LLM to extract lead information from email content
    3. Matches leads to sales agents (if enabled)
    4. Creates persons and tasks in CRM with reasoning notes
    5. Marks processed emails as read (if configured)
    
    Args:
        max_emails: Maximum number of emails to process (default: 50, max: 100)
        match_sales_agent: Whether to match leads to sales agents (default: True)
        db: Database session
    
    Returns:
        Processing results with success/failure counts
    """
    try:
        service = LeadService(db)
        results = await service.process_emails_to_leads(
            max_emails=max_emails,
            match_sales_agent=match_sales_agent
        )
        
        return {
            "message": "Email processing completed",
            "results": results
        }
    except ValueError as e:
        logger.error(f"[red]Error processing emails:[/red] {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[red]Error processing emails:[/red] {e}")
        raise HTTPException(status_code=500, detail=str(e))
