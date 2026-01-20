"""
Lead service for managing leads and syncing to CRM
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.database.models.database import Lead
from app.external.crm.client import CRMClient
from app.external.crm.twenty_crm import lead_to_twenty_crm
from app.services.llm_service import LLMService
from app.core.config import settings
from app.utils.logging import get_logger, app_logger

logger = get_logger(__name__)


class LeadService:
    """Service for managing leads and syncing to Twenty CRM"""
    
    def __init__(self, db: Session):
        self.db = db
        self.crm_client = CRMClient()
        self.llm_service = LLMService()
    
    def get_all_leads(
        self,
        skip: int = 0,
        limit: int = 100,
        synced: Optional[bool] = None
    ) -> List[Lead]:
        """
        Get all leads from the database.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            synced: Filter by sync status (if a synced column exists)
        
        Returns:
            List of Lead objects
        """
        query = self.db.query(Lead)
        
        # Add sync filter if needed (when synced column is added)
        # if synced is not None:
        #     query = query.filter(Lead.synced_to_crm == synced)
        
        return query.offset(skip).limit(limit).all()
    
    def get_lead_by_id(self, lead_id: int) -> Optional[Lead]:
        """Get a lead by database ID"""
        return self.db.query(Lead).filter(Lead.id == lead_id).first()
    
    def get_lead_by_lead_id(self, lead_id: str) -> Optional[Lead]:
        """Get a lead by lead_id (external ID)"""
        return self.db.query(Lead).filter(Lead.lead_id == lead_id).first()
    
    def get_sales_agents(self) -> List[Dict[str, Any]]:
        """
        Get list of available sales agents from configuration.
        
        Returns:
            List of sales agent dictionaries
        """
        agents = []
        for agent in settings.sales_agents:
            agent_dict = {
                "id": agent.id,
                "agent_id": agent.id,  # Alias for compatibility
                "name": agent.name,
                "agent_name": agent.name,  # Alias for compatibility
            }
            if agent.specialization:
                agent_dict["specialization"] = agent.specialization
            if agent.expertise:
                agent_dict["expertise"] = agent.expertise
            if agent.experience_years is not None:
                agent_dict["experience_years"] = agent.experience_years
            if agent.location:
                agent_dict["location"] = agent.location
            if agent.territory:
                agent_dict["territory"] = agent.territory
            if agent.current_workload is not None:
                agent_dict["current_workload"] = agent.current_workload
            if agent.success_rate is not None:
                agent_dict["success_rate"] = agent.success_rate
            if agent.vehicle_types:
                agent_dict["vehicle_types"] = agent.vehicle_types
            if agent.communication_style:
                agent_dict["communication_style"] = agent.communication_style
            
            agents.append(agent_dict)
        
        return agents
    
    async def match_lead_to_sales_agent(
        self,
        lead: Lead,
        version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Match a lead to the best sales agent using LLM.
        
        Args:
            lead: Lead model instance
            version: Prompt version to use (defaults to configured version)
        
        Returns:
            Dictionary containing selected agent and analysis
        """
        sales_agents = self.get_sales_agents()
        
        if not sales_agents:
            logger.warning("[yellow]⚠️  No sales agents configured. Cannot match lead.[/yellow]")
            return {
                "selected_agent_id": None,
                "selected_agent_name": None,
                "error": "No sales agents configured"
            }
        
        logger.info(
            f"[cyan]Matching lead {lead.lead_id} to sales agent...[/cyan] "
            f"[dim]Evaluating {len(sales_agents)} agents[/dim]"
        )
        
        try:
            result = await self.llm_service.match_lead_to_sales_agent(
                lead_data=lead,
                sales_agents=sales_agents,
                version=version
            )
            
            logger.info(
                f"[green]✅ Lead {lead.lead_id} matched to agent:[/green] "
                f"[bold cyan]{result.get('selected_agent_name', 'N/A')}[/bold cyan]"
            )
            
            return result
        except Exception as e:
            logger.error(
                f"[red]❌ Failed to match lead {lead.lead_id} to sales agent:[/red] {e}"
            )
            raise
    
    async def sync_lead_to_crm(self, lead: Lead, match_sales_agent: bool = True) -> dict:
        """
        Sync a single lead to Twenty CRM.
        Creates a person (or uses existing if duplicate) and then creates a task for that person.
        Optionally matches the lead to a sales agent before syncing.
        
        Args:
            lead: Lead model instance
            match_sales_agent: Whether to match lead to sales agent before syncing (default: True)
        
        Returns:
            Dictionary with person and task creation responses, and optionally sales agent match
        """
        sales_agent_match = None
        
        # Match lead to sales agent if requested
        if match_sales_agent:
            try:
                sales_agent_match = await self.match_lead_to_sales_agent(lead)
                logger.info(
                    f"[cyan]Sales agent matched for lead {lead.lead_id}:[/cyan] "
                    f"{sales_agent_match.get('selected_agent_name', 'N/A')}"
                )
            except Exception as e:
                logger.warning(
                    f"[yellow]⚠️  Sales agent matching failed for lead {lead.lead_id}:[/yellow] {e}. "
                    f"Continuing with CRM sync..."
                )
                # Don't fail the sync if matching fails
        from app.external.crm.twenty_crm import lead_to_twenty_crm, lead_to_task_data
        import httpx
        
        person_response = None
        person_id = None
        person_created = False
        
        try:
            # Convert lead to Twenty CRM format
            crm_data = lead_to_twenty_crm(lead)
            
            # Try to create person in Twenty CRM with upsert=true query parameter
            # This allows creating or updating the person (recreates deleted persons)
            try:
                person_response = await self.crm_client.create_record(
                    endpoint="rest/people",
                    data=crm_data,
                    params={"upsert": True}  # Query parameter to enable upsert
                )
                person_created = True
                logger.info(
                    f"[green]✅ Successfully created person in CRM:[/green] "
                    f"[cyan]{lead.lead_id}[/cyan] - {lead.full_name or lead.email}"
                )
            except httpx.HTTPStatusError as e:
                # Handle duplicate entry error (400 Bad Request with duplicate message)
                # IMPORTANT: Only treat as duplicate if error explicitly says so
                # If person was deleted, there will be NO duplicate error - it will create successfully
                if e.response.status_code == 400:
                    try:
                        error_data = e.response.json()
                        error_messages = error_data.get("messages", [])
                        error_text = " ".join(error_messages).lower() + " " + str(error_data).lower() + " " + e.response.text.lower()
                    except:
                        error_text = e.response.text.lower()
                    
                    # Check for specific duplicate indicators - be very specific
                    is_duplicate = (
                        "duplicate entry" in error_text or 
                        "duplicate entry was detected" in error_text or
                        ("duplicate" in error_text and "entry" in error_text) or
                        ("already exists" in error_text and "person" in error_text)
                    )
                    
                    if is_duplicate:
                        logger.warning(
                            f"[yellow]⚠️  Person already exists in CRM (duplicate detected):[/yellow] "
                            f"[cyan]{lead.lead_id}[/cyan] - {lead.full_name or lead.email}. "
                            f"Skipping person creation, continuing with task creation..."
                        )
                        # Person already exists - we'll create the task without person_id
                        # This is acceptable - the task can still be created
                        person_response = None
                        person_id = None
                        person_created = False
                    else:
                        # Other 400 errors - this might be a validation error or something else
                        # Log the full error and re-raise so we know what went wrong
                        logger.error(
                            f"[red]❌ Failed to create person (400 Bad Request):[/red] "
                            f"[cyan]{lead.lead_id}[/cyan] - {lead.full_name or lead.email}"
                        )
                        logger.error(f"[dim]Error details:[/dim] {e.response.text}")
                        # Re-raise to fail the sync - this is not a duplicate, something else is wrong
                        raise
                else:
                    # Other HTTP errors (not 400) - re-raise
                    logger.error(
                        f"[red]❌ Failed to create person (HTTP {e.response.status_code}):[/red] "
                        f"[cyan]{lead.lead_id}[/cyan] - {lead.full_name or lead.email}"
                    )
                    logger.error(f"[dim]Error details:[/dim] {e.response.text}")
                    raise
            except httpx.HTTPError as e:
                # Network or other HTTP errors
                logger.error(
                    f"[red]❌ HTTP error creating person:[/red] "
                    f"[cyan]{lead.lead_id}[/cyan] - {lead.full_name or lead.email} - {str(e)}"
                )
                raise
            
            # Extract person ID from response
            if person_response and isinstance(person_response, dict):
                # Try common field names for person ID
                person_id = (
                    person_response.get("id") or 
                    person_response.get("personId") or 
                    person_response.get("person") or
                    person_response.get("data", {}).get("id") if isinstance(person_response.get("data"), dict) else None
                )
                
                # If person_id is still None, log the response structure for debugging
                if not person_id:
                    logger.debug(f"[dim]Person response structure:[/dim] {person_response}")
                    logger.warning(
                        f"[yellow]⚠️  Could not extract person ID from response. "
                        f"Task may not be linked to person.[/yellow]"
                    )
            
            # Create task for this person (include sales agent match info if available)
            task_data = lead_to_task_data(
                lead, 
                person_id=person_id,
                sales_agent_match=sales_agent_match
            )
            
            # Log task data for debugging
            logger.debug(f"[dim]Task data before sending to CRM:[/dim] {task_data}")
            if sales_agent_match:
                logger.info(
                    f"[cyan]Task includes sales agent match:[/cyan] "
                    f"{sales_agent_match.get('selected_agent_name', 'N/A')}"
                )
            
            try:
                task_response = await self.crm_client.create_record(
                    endpoint="rest/tasks",
                    data=task_data
                )
                
                logger.info(
                    f"[green]✅ Successfully created task in CRM:[/green] "
                    f"[cyan]Task: {task_data['title']}[/cyan] for person {person_id or 'N/A'}"
                )
                
                return {
                    "person": person_response,
                    "person_created": person_created,
                    "task": task_response,
                    "person_id": person_id,
                    "sales_agent_match": sales_agent_match
                }
                
            except Exception as task_error:
                # Log task creation error but don't fail the whole sync
                logger.warning(
                    f"[yellow]⚠️  Person {'created' if person_created else 'found'} but task creation failed:[/yellow] "
                    f"[cyan]{lead.lead_id}[/cyan] - {str(task_error)}"
                )
                # Return person response even if task creation failed
                return {
                    "person": person_response,
                    "person_created": person_created,
                    "task": None,
                    "task_error": str(task_error),
                    "person_id": person_id,
                    "sales_agent_match": sales_agent_match
                }
            
        except Exception as e:
            logger.error(
                f"[red]❌ Failed to sync lead to CRM:[/red] "
                f"[cyan]{lead.lead_id}[/cyan] - {str(e)}"
            )
            raise
    
    async def sync_all_leads_to_crm(
        self,
        skip: int = 0,
        limit: Optional[int] = None
    ) -> dict:
        """
        Sync all leads from database to Twenty CRM.
        
        Args:
            skip: Number of leads to skip
            limit: Maximum number of leads to sync (None for all)
        
        Returns:
            Dictionary with sync results
        """
        app_logger.info(f"[cyan]Starting sync of leads to Twenty CRM...[/cyan]")
        
        leads = self.get_all_leads(skip=skip, limit=limit or 1000)
        total = len(leads)
        
        if total == 0:
            app_logger.warning("[yellow]No leads found to sync[/yellow]")
            return {
                "total": 0,
                "success": 0,
                "failed": 0,
                "results": []
            }
        
        app_logger.info(f"[cyan]Found {total} leads to sync[/cyan]")
        
        results = {
            "total": total,
            "success": 0,
            "failed": 0,
            "results": []
        }
        
        for idx, lead in enumerate(leads, 1):
            try:
                app_logger.info(
                    f"[cyan][{idx}/{total}][/cyan] "
                    f"Syncing lead: [yellow]{lead.lead_id}[/yellow] - "
                    f"{lead.full_name or lead.email or 'N/A'}"
                )
                
                response = await self.sync_lead_to_crm(lead)
                results["success"] += 1
                results["results"].append({
                    "lead_id": lead.lead_id,
                    "status": "success",
                    "crm_response": response
                })
                
            except Exception as e:
                results["failed"] += 1
                results["results"].append({
                    "lead_id": lead.lead_id,
                    "status": "failed",
                    "error": str(e)
                })
                logger.error(f"[red]Failed to sync lead {lead.lead_id}:[/red] {e}")
        
        app_logger.info(
            f"[green]Sync completed:[/green] "
            f"[cyan]{results['success']}[/cyan] successful, "
            f"[red]{results['failed']}[/red] failed out of {total} total"
        )
        
        return results
