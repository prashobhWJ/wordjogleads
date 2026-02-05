"""
Twenty CRM specific models and utilities
"""
from typing import Optional, List, Dict, Any, Tuple
from app.utils.logging import get_logger
from app.services.llm_service import LLMService
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


async def lead_to_task_data(
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
    
    # Determine primary language from sales agent match
    primary_language = "English"  # Default to English
    if sales_agent_match:
        assignment_message = sales_agent_match.get("assignment_message")
        if assignment_message:
            primary_language = assignment_message.get("primary_language", "English")
    
    # Helper function to translate content lines (not headers)
    async def translate_content_lines(lines: List[str], target_language: str) -> List[str]:
        """Translate content lines to target language, preserving structure"""
        if target_language.lower() == "english":
            return lines
        
        # Join lines for translation
        content_text = "\n".join(lines)
        if not content_text.strip():
            return lines
        
        try:
            llm_service = LLMService()
            translation_prompt = f"""Translate ONLY the text content in the following lines to {target_language}. 
Preserve all markdown formatting exactly:
- Keep **bold** markers exactly as they are
- Keep colons (:) exactly as they are  
- Keep numbers and scores exactly as they are
- Only translate the English words, not the markdown syntax

Lines to translate:
{content_text}"""
            
            translated = await llm_service.simple_prompt(
                prompt=translation_prompt,
                system_prompt=f"You are a professional translator. Translate ONLY the text content to {target_language}, preserving all markdown formatting, colons, numbers, and structure exactly."
            )
            
            # Split back into lines
            translated_lines = translated.strip().split("\n")
            return translated_lines if translated_lines else lines
        except Exception as e:
            logger.warning(f"[yellow]⚠️  Failed to translate content to {target_language}:[/yellow] {e}")
            return lines
    
    # Build content sections separately for primary language and English
    primary_parts = []
    english_parts = []
    
    # Lead Information Section
    lead_info_english_lines = []
    lead_info_english_lines.append(f"**Name:** {full_name}")
    if lead.email:
        lead_info_english_lines.append(f"**Email:** {lead.email}")
    if lead.phone:
        lead_info_english_lines.append(f"**Phone:** {lead.phone}")
    if lead.vehicle_type:
        lead_info_english_lines.append(f"**Vehicle Interest:** {lead.vehicle_type}")
    if lead.city or lead.state_province:
        location = ", ".join(filter(None, [lead.city, lead.state_province]))
        lead_info_english_lines.append(f"**Location:** {location}")
    if lead.company_name:
        lead_info_english_lines.append(f"**Company:** {lead.company_name}")
    if lead.employment_status:
        lead_info_english_lines.append(f"**Employment Status:** {lead.employment_status}")
    
    # Translate lead info content
    lead_info_primary_lines = await translate_content_lines(lead_info_english_lines, primary_language)
    
    # Build sections for both languages
    if primary_language.lower() != "english":
        # Primary language section
        primary_parts.append("### 👤 LEAD INFORMATION")
        primary_parts.extend(lead_info_primary_lines)
        # English section (will be added after primary)
        english_parts.append("### 👤 LEAD INFORMATION")
        english_parts.extend(lead_info_english_lines)
    else:
        # If primary is English, just use English
        english_parts.append("### 👤 LEAD INFORMATION")
        english_parts.extend(lead_info_english_lines)
    
    # Sales Agent Assignment Section (if available)
    if sales_agent_match and sales_agent_match.get("selected_agent_id"):
        selected_agent_name = sales_agent_match.get("selected_agent_name", "Unknown")
        selected_agent_id = sales_agent_match.get("selected_agent_id", "N/A")
        confidence_score = sales_agent_match.get("confidence_score", "N/A")
        reasoning = sales_agent_match.get("reasoning", "No reasoning provided")
        
        # Build English assignment content lines
        assignment_english_lines = []
        assignment_english_lines.append(f"**Assigned Agent:** {selected_agent_name}")
        assignment_english_lines.append(f"**Agent ID:** {selected_agent_id}")
        assignment_english_lines.append(f"**Confidence Score:** {confidence_score}/10")
        assignment_english_lines.append("")
        assignment_english_lines.append("### 📋 Assignment Reasoning")
        assignment_english_lines.append(f"{reasoning}")
        
        # Add alternative agents if available
        alternative_agents = sales_agent_match.get("alternative_agents", [])
        if alternative_agents:
            assignment_english_lines.append("")
            assignment_english_lines.append("### 🔄 Alternative Agents")
            for alt_agent in alternative_agents[:3]:  # Limit to top 3 alternatives
                alt_name = alt_agent.get("agent_name", alt_agent.get("agent_id", "Unknown"))
                alt_reason = alt_agent.get("reason", "Alternative option")
                assignment_english_lines.append(f"- **{alt_name}:** {alt_reason}")
        
        # Translate assignment content
        assignment_primary_lines = await translate_content_lines(assignment_english_lines, primary_language)
        
        # Add assignment section to both languages
        if primary_language.lower() != "english":
            # Primary language section
            primary_parts.append("")
            primary_parts.append("---")
            primary_parts.append("")
            primary_parts.append("### 🎯 SALES AGENT ASSIGNMENT")
            primary_parts.extend(assignment_primary_lines)
            # English section (will be added after primary)
            english_parts.append("")
            english_parts.append("---")
            english_parts.append("")
            english_parts.append("### 🎯 SALES AGENT ASSIGNMENT")
            english_parts.extend(assignment_english_lines)
        else:
            # If primary is English, just use English
            english_parts.append("")
            english_parts.append("---")
            english_parts.append("")
            english_parts.append("### 🎯 SALES AGENT ASSIGNMENT")
            english_parts.extend(assignment_english_lines)
    
    # Build final markdown: Primary language first, then English
    markdown_parts = []
    
    if primary_language.lower() != "english":
        # Add primary language section header
        markdown_parts.append(f"## {primary_language.upper()}")
        markdown_parts.append("")
        markdown_parts.extend(primary_parts)
        # Add separator
        markdown_parts.append("")
        markdown_parts.append("---")
        markdown_parts.append("")
        # Add English section header
        markdown_parts.append("## ENGLISH")
        markdown_parts.append("")
        markdown_parts.extend(english_parts)
    else:
        # If primary is English, just use English content
        markdown_parts.extend(english_parts)
    
    # Join all parts to create final markdown content
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
    
    # Extract sales representative name from sales agent match
    sales_representative_name = None
    if sales_agent_match and sales_agent_match.get("selected_agent_name"):
        sales_representative_name = sales_agent_match.get("selected_agent_name")
    
    # Log sales agent match status for debugging
    if sales_agent_match:
        logger.info(
            f"[cyan]Sales agent match data available:[/cyan] "
            f"Agent: {sales_agent_match.get('selected_agent_name', 'N/A')}, "
            f"Has reasoning: {bool(sales_agent_match.get('reasoning'))}"
        )
        logger.debug(f"[dim]Full sales agent match data:[/dim] {sales_agent_match}")
        if sales_representative_name:
            logger.info(f"[cyan]salesrep field will be set to:[/cyan] {sales_representative_name}")
    else:
        logger.warning("[yellow]⚠️  No sales agent match data provided to task creation[/yellow]")
    
    # Create and validate the task schema
    # Note: taskTargets is excluded as it cannot be set via REST API during creation
    task_create = TwentyCRMTaskCreate(
        title=task_name,
        status="BACKLOG",
        assigneeId=None,  # assigneeId is for workspace member, not person
        bodyV2=body_v2,
        taskTargets=None,  # Cannot be set via REST API - must be linked separately
        salesrep=sales_representative_name  # Sales representative name only
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
    logger.info(f"[dim]  salesrep: {task_dict.get('salesrep', 'Not set')}[/dim]")
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
