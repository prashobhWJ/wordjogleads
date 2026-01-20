"""
Twenty CRM specific models and utilities
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Tuple


class TwentyCRMName(BaseModel):
    """Name structure for Twenty CRM"""
    firstName: str
    lastName: str


class TwentyCRMEmails(BaseModel):
    """Email structure for Twenty CRM"""
    primaryEmail: str
    additionalEmails: Optional[List[str]] = None


class TwentyCRMLink(BaseModel):
    """Link structure for Twenty CRM"""
    primaryLinkLabel: str = ""
    primaryLinkUrl: str = ""
    secondaryLinks: List[Dict[str, Any]] = []


class TwentyCRMPhones(BaseModel):
    """Phone structure for Twenty CRM"""
    primaryPhoneNumber: str
    primaryPhoneCallingCode: Optional[str] = None
    primaryPhoneCountryCode: Optional[str] = None
    additionalPhones: List[Dict[str, Any]] = []


class TwentyCRMPersonCreate(BaseModel):
    """Model for creating a person in Twenty CRM"""
    name: TwentyCRMName
    emails: TwentyCRMEmails
    linkedinLink: Optional[TwentyCRMLink] = None
    xLink: Optional[TwentyCRMLink] = None
    phones: Optional[TwentyCRMPhones] = None


class TwentyCRMTaskCreate(BaseModel):
    """Model for creating a task in Twenty CRM"""
    title: str
    status: str = "BACKLOG"
    assigneeId: Optional[str] = None  # Person ID to assign the task to


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
    
    Args:
        lead: Lead model instance from database
    
    Returns:
        Dictionary in Twenty CRM format
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
    
    # Build the Twenty CRM payload - matching exact format from curl example
    payload = {
        "name": {
            "firstName": first_name or "Unknown",
            "lastName": last_name or "Unknown"
        },
        "emails": {
            "primaryEmail": lead.email or "",
            "additionalEmails": None
        },
        "linkedinLink": {
            "primaryLinkLabel": "",
            "primaryLinkUrl": "",
            "secondaryLinks": []
        },
        "xLink": {
            "primaryLinkLabel": "",
            "primaryLinkUrl": "",
            "secondaryLinks": []
        }
    }
    
    # Add phone if available
    # Note: Twenty CRM prefers unformatted numbers to avoid conflicts
    if phone_number and calling_code and country_code:
        # Send digits only to avoid formatting conflicts with country code inference
        # Twenty CRM will format it based on the country code
        payload["phones"] = {
            "primaryPhoneNumber": phone_number,  # Send digits only, no formatting
            "primaryPhoneCallingCode": calling_code,
            "primaryPhoneCountryCode": country_code,
            "additionalPhones": []
        }
    elif phone_number:
        # If we have a number but no country info, send it as-is
        payload["phones"] = {
            "primaryPhoneNumber": phone_number,
            "primaryPhoneCallingCode": calling_code,
            "primaryPhoneCountryCode": country_code,
            "additionalPhones": []
        }
    
    return payload


def lead_to_task_data(lead, person_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Convert a Lead to a task data structure for Twenty CRM.
    Task name will be the lead's full name.
    
    Args:
        lead: Lead model instance from database
        person_id: Optional person ID to link the task to
    
    Returns:
        Dictionary in Twenty CRM task format matching curl example
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
    
    # Task data matching the curl format
    # Based on curl example: {"status": "BACKLOG"}
    # But we need to add the task name/title
    task_data = {
        "status": "BACKLOG"
    }
    
    # Add task title/name - try common field names
    # Some APIs use "title", others use "name" or "subject"
    task_data["title"] = task_name
    
    # Link task to person if person_id is provided
    # Try common field names for linking to person
    if person_id:
        # Try assigneeId (most common for task assignment)
        task_data["assigneeId"] = person_id
        # Also try personId as alternative (for linking)
        task_data["personId"] = person_id
    
    return task_data
