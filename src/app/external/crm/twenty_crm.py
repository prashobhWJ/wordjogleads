"""
Twenty CRM specific models and utilities
"""
from typing import Optional, List, Dict, Any, Tuple
from app.utils.logging import get_logger
from app.schemas.twenty_crm import (
    TwentyCRMName,
    TwentyCRMEmails,
    TwentyCRMLink,
    TwentyCRMPhones,
    TwentyCRMPersonCreate,
    TwentyCRMTaskCreate
)

logger = get_logger(__name__)


def parse_phone_number(phone: str, country_code: Optional[str] = None) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Parse phone number into number, calling code, and country code.
    Handles formats like "(519) 717-4414" or "+33 06 10 20 30 40" or "06 10 20 30 40"
    
    Args:
        phone: Phone number string
        country_code: Optional country code from lead data (e.g., "ON", "CA", "US")
    
    Returns:
        Tuple of (phone_number, calling_code, country_code)
    """
    if not phone:
        return "", None, None
    
    # Map province/state codes to country codes
    province_to_country = {
        "ON": "CA",  # Ontario, Canada
        "QC": "CA",  # Quebec, Canada
        "BC": "CA",  # British Columbia, Canada
        "AB": "CA",  # Alberta, Canada
        "MB": "CA",  # Manitoba, Canada
        "SK": "CA",  # Saskatchewan, Canada
        "NS": "CA",  # Nova Scotia, Canada
        "NB": "CA",  # New Brunswick, Canada
        "NL": "CA",  # Newfoundland and Labrador, Canada
        "PE": "CA",  # Prince Edward Island, Canada
        "YT": "CA",  # Yukon, Canada
        "NT": "CA",  # Northwest Territories, Canada
        "NU": "CA",  # Nunavut, Canada
    }
    
    # Normalize country code
    if country_code:
        country_code = country_code.upper()
        # Convert province code to country code
        if country_code in province_to_country:
            country_code = province_to_country[country_code]
    
    # Remove common formatting but keep spaces for now
    phone_clean = phone.strip()
    phone_digits = phone_clean.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    
    # Try to extract country code if starts with +
    if phone_clean.startswith("+"):
        # Remove + and parse
        phone_without_plus = phone_digits
        
        if phone_without_plus.startswith("1") and len(phone_without_plus) == 11:  # North America
            number = phone_without_plus[1:]
            # Use provided country code or default to US
            final_country = country_code or "US"
            return number, "+1", final_country
        elif phone_without_plus.startswith("33") and len(phone_without_plus) >= 10:  # France
            number = phone_without_plus[2:]
            if number.startswith("0"):
                number = number[1:]
            return number, "+33", "FR"
        elif phone_without_plus.startswith("44"):  # UK
            number = phone_without_plus[2:]
            if number.startswith("0"):
                number = number[1:]
            return number, "+44", "GB"
        else:
            # Try to detect country code (first 1-3 digits)
            return phone_without_plus, None, None
    
    # Handle French format without + (e.g., "06 10 20 30 40")
    if phone_digits.startswith("0") and len(phone_digits) == 10:
        # Remove leading 0 for French numbers
        return phone_digits[1:], "+33", "FR"
    
    # North America format (10 digits) - need to detect US vs CA
    if len(phone_digits) == 10 and phone_digits.isdigit():
        # Canadian area codes (common ones)
        canadian_area_codes = {
            "204", "226", "236", "249", "250", "289", "306", "343", "365", "403",
            "416", "418", "431", "437", "438", "450", "506", "514", "519", "548",
            "579", "581", "587", "604", "613", "639", "647", "672", "705", "709",
            "742", "753", "778", "780", "782", "807", "819", "825", "867", "873",
            "902", "905", "942"
        }
        
        area_code = phone_digits[:3]
        
        # If we have a country code from lead data, use it
        if country_code:
            return phone_digits, "+1", country_code
        # Otherwise, try to detect from area code
        elif area_code in canadian_area_codes:
            return phone_digits, "+1", "CA"
        else:
            # Default to US for unknown area codes
            return phone_digits, "+1", "US"
    
    # Return cleaned number without country code if we can't determine
    return phone_digits, None, None


def lead_to_twenty_crm(lead) -> Dict[str, Any]:
    """
    Convert a Lead database model to Twenty CRM format.
    Uses Pydantic schemas for validation.
    
    Args:
        lead: Lead model instance from database
    
    Returns:
        Dictionary in Twenty CRM format (validated by TwentyCRMPersonCreate schema)
    """
    # Parse name
    first_name = lead.first_name or ""
    last_name = lead.last_name or ""
    
    # If we only have full_name, try to split it
    if not first_name and not last_name and lead.full_name:
        name_parts = lead.full_name.split(" ", 1)
        first_name = name_parts[0] if len(name_parts) > 0 else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""
    
    # Parse phone number - use country_code from lead if available
    lead_country_code = lead.country_code or lead.country
    phone_number, calling_code, country_code = parse_phone_number(
        lead.phone or "",
        country_code=lead_country_code
    )
    
    # Build schema objects for validation
    name = TwentyCRMName(
        firstName=first_name or "Unknown",
        lastName=last_name or "Unknown"
    )
    
    emails = TwentyCRMEmails(
        primaryEmail=lead.email or "",
        additionalEmails=None
    )
    
    linkedin_link = TwentyCRMLink(
        primaryLinkLabel="",
        primaryLinkUrl="",
        secondaryLinks=[]
    )
    
    x_link = TwentyCRMLink(
        primaryLinkLabel="",
        primaryLinkUrl="",
        secondaryLinks=[]
    )
    
    # Build phones if available
    phones = None
    if phone_number:
        phones = TwentyCRMPhones(
            primaryPhoneNumber=phone_number,
            primaryPhoneCallingCode=calling_code,
            primaryPhoneCountryCode=country_code,
            additionalPhones=[]
        )
    
    # Create and validate the person schema
    person_create = TwentyCRMPersonCreate(
        name=name,
        emails=emails,
        linkedinLink=linkedin_link,
        xLink=x_link,
        phones=phones
    )
    
    # Return as dict (Pydantic model_dump)
    return person_create.model_dump(exclude_none=False)


def lead_to_task_data(
    lead, 
    person_id: Optional[str] = None,
    sales_agent_match: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convert a Lead to a task data structure for Twenty CRM.
    Uses Pydantic schemas for validation.
    Task name will be the lead's full name.
    Optionally includes sales agent matching information in task content.
    
    Args:
        lead: Lead model instance from database
        person_id: Optional person ID to link the task to
        sales_agent_match: Optional sales agent match result from LLM
    
    Returns:
        Dictionary in Twenty CRM task format (validated by TwentyCRMTaskCreate schema)
    """
    # Use full name or construct from first/last name
    task_name = lead.full_name or ""
    if not task_name:
        if lead.first_name and lead.last_name:
            task_name = f"{lead.first_name} {lead.last_name}"
        elif lead.first_name:
            task_name = lead.first_name
        elif lead.last_name:
            task_name = lead.last_name
        else:
            task_name = lead.email or lead.lead_id or "Unknown Lead"
    
    # Build task content with lead information and sales agent assignment
    # Format as professional markdown
    
    # Get lead full name
    full_name = lead.full_name or ""
    if not full_name:
        if lead.first_name and lead.last_name:
            full_name = f"{lead.first_name} {lead.last_name}"
        elif lead.first_name:
            full_name = lead.first_name
        elif lead.last_name:
            full_name = lead.last_name
        else:
            full_name = lead.email or lead.lead_id or "Unknown Lead"
    
    # Build markdown content
    markdown_parts = []
    
    # Lead Information Section
    markdown_parts.append("### 👤 LEAD INFORMATION\n")
    markdown_parts.append(f"**Name:** {full_name}")
    if lead.email:
        markdown_parts.append(f"**Email:** {lead.email}")
    if lead.phone:
        markdown_parts.append(f"**Phone:** {lead.phone}")
    if lead.vehicle_type:
        markdown_parts.append(f"**Vehicle Interest:** {lead.vehicle_type}")
    if lead.city or lead.state_province:
        location = ", ".join(filter(None, [lead.city, lead.state_province]))
        markdown_parts.append(f"**Location:** {location}")
    if lead.company_name:
        markdown_parts.append(f"**Company:** {lead.company_name}")
    if lead.employment_status:
        markdown_parts.append(f"**Employment Status:** {lead.employment_status}")
    
    # Add sales agent assignment section if available
    if sales_agent_match and sales_agent_match.get("selected_agent_id"):
        markdown_parts.append("\n---\n")
        markdown_parts.append("### 🎯 SALES AGENT ASSIGNMENT\n")
        
        selected_agent_name = sales_agent_match.get("selected_agent_name", "Unknown")
        selected_agent_id = sales_agent_match.get("selected_agent_id", "N/A")
        confidence_score = sales_agent_match.get("confidence_score", "N/A")
        reasoning = sales_agent_match.get("reasoning", "No reasoning provided")
        
        markdown_parts.append(f"**Assigned Agent:** {selected_agent_name}")
        markdown_parts.append(f"**Agent ID:** {selected_agent_id}")
        markdown_parts.append(f"**Confidence Score:** {confidence_score}/10\n")
        
        markdown_parts.append("### 📋 Assignment Reasoning\n")
        markdown_parts.append(f"{reasoning}\n")
        
        # Add alternative agents if available
        alternative_agents = sales_agent_match.get("alternative_agents", [])
        if alternative_agents:
            markdown_parts.append("\n### 🔄 Alternative Agents\n")
            for alt_agent in alternative_agents[:3]:  # Limit to top 3 alternatives
                alt_name = alt_agent.get("agent_name", alt_agent.get("agent_id", "Unknown"))
                alt_reason = alt_agent.get("reason", "Alternative option")
                markdown_parts.append(f"- **{alt_name}:** {alt_reason}")
    
    # Join all parts with newlines to create markdown content
    # Format using f-string style like the example provided
    markdown_content = "\n".join(markdown_parts) if markdown_parts else "Lead sync from Carnance API"
    
    # Build bodyV2 structure for task content
    # Format: Use f-string style markdown formatting as shown in example
    # Only include markdown field, not blocknote
    body_v2 = {
        "markdown": markdown_content
    }
    
    # Log the content being created for debugging
    logger.info(f"[cyan]bodyV2 content created:[/cyan] {len(markdown_content)} characters")
    logger.debug(f"[dim]bodyV2 markdown preview:[/dim] {markdown_content[:500]}...")
    
    # Note: taskTargets cannot be set via REST API during task creation
    # The error "One-to-many relation taskTargets field does not support write operations" 
    # indicates we must link tasks to persons through a different method (likely GraphQL or separate API call)
    # For now, we'll skip taskTargets in the creation payload
    task_targets = None
    
    # Log sales agent match status for debugging
    if sales_agent_match:
        logger.info(
            f"[cyan]Sales agent match data available:[/cyan] "
            f"Agent: {sales_agent_match.get('selected_agent_name', 'N/A')}, "
            f"Has reasoning: {bool(sales_agent_match.get('reasoning'))}"
        )
        logger.debug(f"[dim]Full sales agent match data:[/dim] {sales_agent_match}")
    else:
        logger.warning("[yellow]⚠️  No sales agent match data provided to task creation[/yellow]")
    
    # Create and validate the task schema
    # Note: taskTargets is excluded as it cannot be set via REST API during creation
    task_create = TwentyCRMTaskCreate(
        title=task_name,
        status="BACKLOG",
        assigneeId=None,  # assigneeId is for workspace member, not person
        bodyV2=body_v2,
        taskTargets=None  # Cannot be set via REST API - must be linked separately
    )
    
    # Return as dict (Pydantic model_dump)
    # Use exclude_none=True to exclude None values (like taskTargets)
    task_dict = task_create.model_dump(exclude_none=True)
    
    # Remove taskTargets if it exists (cannot be set via REST API)
    if 'taskTargets' in task_dict:
        del task_dict['taskTargets']
        logger.debug("[dim]Removed taskTargets from payload (not supported via REST API)[/dim]")
    
    # Ensure bodyV2 is included (should already be there from schema)
    if 'bodyV2' not in task_dict or task_dict.get('bodyV2') is None:
        task_dict['bodyV2'] = body_v2
    
    # Verify bodyV2 structure before sending
    if task_dict.get('bodyV2'):
        if not isinstance(task_dict['bodyV2'], dict):
            logger.warning(f"[yellow]bodyV2 is not a dict, converting...[/yellow]")
            task_dict['bodyV2'] = body_v2
        elif not task_dict['bodyV2'].get('markdown'):
            logger.warning(f"[yellow]bodyV2.markdown is missing, adding...[/yellow]")
            task_dict['bodyV2'] = body_v2
    
    # Note: Do NOT add 'body' or 'description' fields - Twenty CRM REST API rejects them
    # Only bodyV2 with markdown field is accepted (no blocknote needed)
    
    # Log what we're sending to the API
    logger.info(f"[cyan]Task data being sent to CRM:[/cyan]")
    logger.info(f"[dim]  Title: {task_dict.get('title')}[/dim]")
    logger.info(f"[dim]  Status: {task_dict.get('status')}[/dim]")
    logger.info(f"[dim]  Has bodyV2: {bool(task_dict.get('bodyV2'))}[/dim]")
    logger.info(f"[dim]  taskTargets: Excluded (not supported via REST API)[/dim]")
    if task_dict.get('bodyV2'):
        body_v2_data = task_dict['bodyV2']
        if isinstance(body_v2_data, dict):
            markdown_preview = body_v2_data.get('markdown', '')[:300]
            logger.info(f"[dim]  bodyV2.markdown ({len(body_v2_data.get('markdown', ''))} chars):[/dim]")
            logger.info(f"[dim]{markdown_preview}...[/dim]")
        else:
            logger.warning(f"[yellow]bodyV2 is not a dict: {type(body_v2_data)}[/yellow]")
    
    line_count = len(markdown_content.split('\n')) if markdown_content else 0
    logger.info(
        f"[green]✅ Task content includes {line_count} lines[/green] "
        f"[dim](includes sales agent info: {bool(sales_agent_match and sales_agent_match.get('selected_agent_id'))})[/dim]"
    )
    
    return task_dict
