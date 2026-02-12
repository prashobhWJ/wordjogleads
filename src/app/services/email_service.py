"""
Email service for reading emails using IMAP/POP3 (read-only)
Supports OAuth2 authentication for Microsoft 365/Outlook
Uses standard imaplib for reliable IMAP operations
"""
import asyncio
import email
import imaplib
from email.header import decode_header
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from app.core.config import settings
from app.utils.logging import get_logger
import re
import httpx
import base64

logger = get_logger(__name__)


def strip_html(html_content: str) -> str:
    """
    Strip HTML tags from email content to get plain text.
    
    Args:
        html_content: HTML content string
    
    Returns:
        Plain text content
    """
    if not html_content:
        return ""
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', html_content)
    
    # Decode common HTML entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    text = text.replace('&apos;', "'")
    
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text


def decode_mime_words(s: str) -> str:
    """
    Decode MIME encoded words in email headers.
    
    Args:
        s: String that may contain MIME encoded words
    
    Returns:
        Decoded string
    """
    if not s:
        return ""
    
    decoded_parts = decode_header(s)
    decoded_string = ""
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            try:
                decoded_string += part.decode(encoding or 'utf-8', errors='ignore')
            except (UnicodeDecodeError, LookupError):
                decoded_string += part.decode('utf-8', errors='ignore')
        else:
            decoded_string += part
    
    return decoded_string


def get_email_body(msg: email.message.Message) -> str:
    """
    Extract plain text body from email message.
    
    Args:
        msg: Email message object
    
    Returns:
        Plain text body content
    """
    body = ""
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            
            # Skip attachments
            if "attachment" in content_disposition:
                continue
            
            # Prefer text/plain, fallback to text/html
            if content_type == "text/plain":
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        body = payload.decode(charset, errors='ignore')
                        break
                except Exception as e:
                    logger.debug(f"[dim]Error decoding text/plain part:[/dim] {e}")
            elif content_type == "text/html" and not body:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        html_body = payload.decode(charset, errors='ignore')
                        body = strip_html(html_body)
                except Exception as e:
                    logger.debug(f"[dim]Error decoding text/html part:[/dim] {e}")
    else:
        # Single part message
        content_type = msg.get_content_type()
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8'
                if content_type == "text/html":
                    html_body = payload.decode(charset, errors='ignore')
                    body = strip_html(html_body)
                else:
                    body = payload.decode(charset, errors='ignore')
        except Exception as e:
            logger.debug(f"[dim]Error decoding single part message:[/dim] {e}")
    
    return body


class EmailService:
    """Service for reading emails using IMAP (read-only)
    Supports OAuth2 authentication for Microsoft 365/Outlook
    Uses standard imaplib for reliable IMAP operations
    """
    
    def __init__(self):
        if not settings.email:
            raise ValueError("Email configuration not found in settings")
        
        self.provider = settings.email.provider.lower()
        self.server = settings.email.server
        self.port = settings.email.port
        self.use_ssl = settings.email.use_ssl
        self.auth_method = settings.email.auth_method.lower() if settings.email.auth_method else "password"
        self.folder = settings.email.folder
        self.read_only = settings.email.read_only
        self.recent_email_minutes = settings.email.recent_email_minutes
        
        # OAuth2 settings
        self.tenant_id = settings.email.tenant_id
        self.client_id = settings.email.client_id
        self.client_secret = settings.email.client_secret
        self.mailbox = settings.email.mailbox
        
        # Basic auth settings
        self.username = settings.email.username
        self.password = settings.email.password
        
        # Validate configuration based on auth method
        if self.auth_method == "oauth2":
            if not all([self.server, self.tenant_id, self.client_id, self.client_secret, self.mailbox]):
                logger.warning(
                    "[yellow]⚠️  OAuth2 email configuration incomplete. "
                    "Please set server, tenant_id, client_id, client_secret, and mailbox in config.yaml[/yellow]"
                )
        else:
            if not all([self.server, self.username, self.password]):
                logger.warning(
                    "[yellow]⚠️  Email configuration incomplete. "
                    "Please set server, username, and password in config.yaml[/yellow]"
                )
    
    async def _get_oauth2_token(self) -> str:
        """
        Get OAuth2 access token for Microsoft 365 using client credentials flow.
        
        Returns:
            OAuth2 access token string
        
        Raises:
            Exception: If token acquisition fails
        """
        if not all([self.tenant_id, self.client_id, self.client_secret]):
            raise ValueError(
                "OAuth2 credentials not configured. "
                "Please set tenant_id, client_id, and client_secret in config.yaml"
            )
        
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        
        # For IMAP access, we need the Mail.Read scope
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://outlook.office365.com/.default",
            "grant_type": "client_credentials"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(token_url, data=data)
                response.raise_for_status()
                token_data = response.json()
                access_token = token_data.get("access_token")
                
                if not access_token:
                    raise ValueError("No access token in response")
                
                logger.debug("[cyan]Successfully obtained OAuth2 access token[/cyan]")
                return access_token
                
        except httpx.HTTPError as e:
            logger.error(f"[red]❌ Failed to get OAuth2 access token:[/red] {e}")
            raise Exception(f"Failed to get OAuth2 access token: {e}")
    
    def _imap_fetch_emails(
        self,
        folder_name: str,
        max_results: Optional[int],
        since_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Synchronous method to connect to IMAP server and fetch unread emails.
        This runs in a thread via asyncio.to_thread() for async compatibility.
        
        Args:
            folder_name: Mailbox folder to read from
            max_results: Maximum number of emails to retrieve
        
        Returns:
            List of email dictionaries
        """
        imap_client = None
        try:
            # Connect to IMAP server
            logger.info(f"[cyan]Connecting to IMAP server:[/cyan] {self.server}:{self.port} (SSL={self.use_ssl})")
            if self.use_ssl:
                imap_client = imaplib.IMAP4_SSL(self.server, self.port)
            else:
                imap_client = imaplib.IMAP4(self.server, self.port)
            
            logger.info(f"[green]✅ Connected to IMAP server:[/green] {self.server}")
            
            # Authenticate based on auth method
            if self.auth_method == "oauth2":
                # OAuth2 authentication - token must be obtained before calling this method
                raise ValueError("OAuth2 requires async token retrieval. Use get_unread_emails() instead.")
            else:
                # Basic authentication
                logger.debug(f"[cyan]Logging in with username:[/cyan] {self.username}")
                try:
                    imap_client.login(self.username, self.password)
                    logger.info(f"[green]✅ Authenticated to IMAP server:[/green] {self.server}")
                except imaplib.IMAP4.error as e:
                    error_msg = str(e)
                    logger.error(f"[red]❌ Login failed:[/red] {error_msg}")
                    raise Exception(
                        f"Authentication failed: {error_msg}\n"
                        f"Please verify:\n"
                        f"1. Username and password are correct\n"
                        f"2. IMAP is enabled in your Outlook account settings\n"
                        f"3. You're using an app-specific password if 2FA is enabled\n"
                        f"4. For Outlook.com, you may need to use OAuth2 instead of basic auth"
                    )
            
            # Select or examine mailbox folder
            logger.debug(f"[cyan]Opening folder:[/cyan] {folder_name} (read_only={self.read_only})")
            if self.read_only:
                # EXAMINE opens mailbox in read-only mode (standard imaplib)
                typ, data = imap_client.select(folder_name, readonly=True)
            else:
                # SELECT opens mailbox in read-write mode
                typ, data = imap_client.select(folder_name, readonly=False)
            
            if typ != 'OK':
                raise Exception(f"Failed to select folder '{folder_name}': {data}")
            
            msg_count = data[0].decode() if data and data[0] else '0'
            logger.info(f"[cyan]Folder '{folder_name}' opened:[/cyan] {msg_count} messages")
            
            # Search for unread emails, optionally filtered by date
            if since_date:
                # Format date as DD-MMM-YYYY for IMAP SINCE search (e.g., "12-Feb-2026")
                since_date_str = since_date.strftime("%d-%b-%Y")
                search_criteria = f'(UNSEEN SINCE {since_date_str})'
                logger.info(f"[cyan]Searching for unread emails since:[/cyan] {since_date_str}")
            else:
                search_criteria = 'UNSEEN'
            
            typ, data = imap_client.search(None, search_criteria)
            
            if typ != 'OK':
                logger.warning(f"[yellow]⚠️  IMAP search failed:[/yellow] {data}")
                return []
            
            # Get list of email IDs
            email_ids_str = data[0].decode() if data[0] else ""
            email_ids = email_ids_str.split() if email_ids_str.strip() else []
            
            if not email_ids:
                logger.info("[yellow]No unread emails found[/yellow]")
                return []
            
            # Limit to max_results if specified (take most recent)
            if max_results is not None:
                email_ids = email_ids[-max_results:] if len(email_ids) > max_results else email_ids
            
            logger.info(
                f"[green]✅ Found {len(email_ids)} unread email(s) in {folder_name}[/green]"
            )
            
            # Fetch emails
            processed_emails = []
            total_emails = len(email_ids)
            logger.info(f"[cyan]Fetching {total_emails} email(s)...[/cyan]")
            
            for idx, eid in enumerate(email_ids, 1):
                try:
                    # Log progress every 10 emails or for the last email
                    if idx % 10 == 0 or idx == total_emails:
                        logger.debug(f"[dim]Fetching email {idx}/{total_emails} (ID: {eid})[/dim]")
                    
                    # Fetch email by ID
                    typ, msg_data = imap_client.fetch(eid, '(RFC822)')
                    
                    if typ != 'OK' or not msg_data or not msg_data[0]:
                        logger.warning(f"[yellow]⚠️  Failed to fetch email {eid}[/yellow]")
                        continue
                    
                    # Parse email message
                    email_body_bytes = msg_data[0][1]
                    msg = email.message_from_bytes(email_body_bytes)
                    
                    # Extract email information
                    subject = decode_mime_words(msg.get("Subject", ""))
                    sender = decode_mime_words(msg.get("From", ""))
                    sender_email_addr = msg.get("From", "")
                    
                    # Extract email address from sender field
                    email_address = sender_email_addr
                    if '<' in sender_email_addr and '>' in sender_email_addr:
                        email_address = sender_email_addr[sender_email_addr.find('<')+1:sender_email_addr.find('>')]
                    
                    # Extract sender name
                    sender_name = sender
                    if '<' in sender:
                        sender_name = sender[:sender.find('<')].strip().strip('"')
                    
                    # Get date
                    date_str = msg.get("Date", "")
                    received_datetime = None
                    if date_str:
                        try:
                            from email.utils import parsedate_to_datetime
                            received_datetime = parsedate_to_datetime(date_str).isoformat()
                        except Exception:
                            received_datetime = date_str
                    
                    # Extract body
                    body = get_email_body(msg)
                    
                    # Check for attachments
                    has_attachments = False
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_disposition = str(part.get("Content-Disposition", ""))
                            if "attachment" in content_disposition:
                                has_attachments = True
                                break
                    
                    processed_email = {
                        "id": eid,
                        "subject": subject,
                        "body": body,
                        "body_preview": body[:500] if body else "",
                        "sender": email_address,
                        "sender_name": sender_name,
                        "received_datetime": received_datetime,
                        "is_read": False,
                        "has_attachments": has_attachments
                    }
                    processed_emails.append(processed_email)
                    
                except Exception as e:
                    logger.warning(
                        f"[yellow]⚠️  Error processing email {eid}:[/yellow] {e}"
                    )
                    continue
            
            return processed_emails
            
        finally:
            # Always close the connection
            if imap_client:
                try:
                    imap_client.close()
                except Exception:
                    pass
                try:
                    imap_client.logout()
                except Exception:
                    pass
    
    def _imap_fetch_emails_oauth2(
        self,
        access_token: str,
        folder_name: str,
        max_results: Optional[int],
        since_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Synchronous method to connect to IMAP server and fetch unread emails using OAuth2.
        This runs in a thread via asyncio.to_thread() for async compatibility.
        
        Args:
            access_token: OAuth2 access token
            folder_name: Mailbox folder to read from
            max_results: Maximum number of emails to retrieve
        
        Returns:
            List of email dictionaries
        """
        imap_client = None
        try:
            # Connect to IMAP server
            logger.info(f"[cyan]Connecting to IMAP server (OAuth2):[/cyan] {self.server}:{self.port}")
            if self.use_ssl:
                imap_client = imaplib.IMAP4_SSL(self.server, self.port)
            else:
                imap_client = imaplib.IMAP4(self.server, self.port)
            
            logger.info(f"[green]✅ Connected to IMAP server:[/green] {self.server}")
            
            # OAuth2 authentication using XOAUTH2
            auth_string = f"user={self.mailbox}\x01auth=Bearer {access_token}\x01\x01"
            
            try:
                imap_client.authenticate('XOAUTH2', lambda x: auth_string.encode('utf-8'))
                logger.info(f"[green]✅ Authenticated to IMAP server with OAuth2:[/green] {self.server}")
            except imaplib.IMAP4.error as e:
                error_msg = str(e)
                logger.error(f"[red]❌ OAuth2 authentication failed:[/red] {error_msg}")
                raise Exception(f"OAuth2 authentication failed: {error_msg}")
            
            # Select or examine mailbox folder
            logger.debug(f"[cyan]Opening folder:[/cyan] {folder_name} (read_only={self.read_only})")
            typ, data = imap_client.select(folder_name, readonly=self.read_only)
            
            if typ != 'OK':
                raise Exception(f"Failed to select folder '{folder_name}': {data}")
            
            msg_count = data[0].decode() if data and data[0] else '0'
            logger.info(f"[cyan]Folder '{folder_name}' opened:[/cyan] {msg_count} messages")
            
            # Search for unread emails, optionally filtered by date
            if since_date:
                # Format date as DD-MMM-YYYY for IMAP SINCE search (e.g., "12-Feb-2026")
                since_date_str = since_date.strftime("%d-%b-%Y")
                search_criteria = f'(UNSEEN SINCE {since_date_str})'
                logger.info(f"[cyan]Searching for unread emails since:[/cyan] {since_date_str}")
            else:
                search_criteria = 'UNSEEN'
            
            typ, data = imap_client.search(None, search_criteria)
            
            if typ != 'OK':
                logger.warning(f"[yellow]⚠️  IMAP search failed:[/yellow] {data}")
                return []
            
            # Get list of email IDs
            email_ids_str = data[0].decode() if data[0] else ""
            email_ids = email_ids_str.split() if email_ids_str.strip() else []
            
            if not email_ids:
                logger.info("[yellow]No unread emails found[/yellow]")
                return []
            
            # Limit to max_results if specified
            if max_results is not None:
                email_ids = email_ids[-max_results:] if len(email_ids) > max_results else email_ids
            
            logger.info(
                f"[green]✅ Found {len(email_ids)} unread email(s) in {folder_name}[/green]"
            )
            
            # Fetch emails
            processed_emails = []
            total_emails = len(email_ids)
            logger.info(f"[cyan]Fetching {total_emails} email(s)...[/cyan]")
            
            for idx, eid in enumerate(email_ids, 1):
                try:
                    # Log progress every 10 emails or for the last email
                    if idx % 10 == 0 or idx == total_emails:
                        logger.debug(f"[dim]Fetching email {idx}/{total_emails} (ID: {eid})[/dim]")
                    
                    typ, msg_data = imap_client.fetch(eid, '(RFC822)')
                    
                    if typ != 'OK' or not msg_data or not msg_data[0]:
                        logger.warning(f"[yellow]⚠️  Failed to fetch email {eid}[/yellow]")
                        continue
                    
                    email_body_bytes = msg_data[0][1]
                    msg = email.message_from_bytes(email_body_bytes)
                    
                    subject = decode_mime_words(msg.get("Subject", ""))
                    sender = decode_mime_words(msg.get("From", ""))
                    sender_email_addr = msg.get("From", "")
                    
                    email_address = sender_email_addr
                    if '<' in sender_email_addr and '>' in sender_email_addr:
                        email_address = sender_email_addr[sender_email_addr.find('<')+1:sender_email_addr.find('>')]
                    
                    sender_name = sender
                    if '<' in sender:
                        sender_name = sender[:sender.find('<')].strip().strip('"')
                    
                    date_str = msg.get("Date", "")
                    received_datetime = None
                    if date_str:
                        try:
                            from email.utils import parsedate_to_datetime
                            received_datetime = parsedate_to_datetime(date_str).isoformat()
                        except Exception:
                            received_datetime = date_str
                    
                    body = get_email_body(msg)
                    
                    has_attachments = False
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_disposition = str(part.get("Content-Disposition", ""))
                            if "attachment" in content_disposition:
                                has_attachments = True
                                break
                    
                    processed_email = {
                        "id": eid,
                        "subject": subject,
                        "body": body,
                        "body_preview": body[:500] if body else "",
                        "sender": email_address,
                        "sender_name": sender_name,
                        "received_datetime": received_datetime,
                        "is_read": False,
                        "has_attachments": has_attachments
                    }
                    processed_emails.append(processed_email)
                    
                except Exception as e:
                    logger.warning(f"[yellow]⚠️  Error processing email {eid}:[/yellow] {e}")
                    continue
            
            return processed_emails
            
        finally:
            if imap_client:
                try:
                    imap_client.close()
                except Exception:
                    pass
                try:
                    imap_client.logout()
                except Exception:
                    pass
    
    async def get_unread_emails(
        self,
        max_results: Optional[int] = 50,
        folder: Optional[str] = None,
        since_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get unread emails from IMAP mailbox (read-only).
        Supports both OAuth2 and basic authentication.
        Uses standard imaplib in a thread for reliability.
        
        Args:
            max_results: Maximum number of emails to retrieve (default: 50, None for all)
            folder: Mailbox folder to read from (default: configured folder or "INBOX")
            since_date: Optional datetime to filter emails by date (IMAP SINCE search)
        
        Returns:
            List of email dictionaries with subject, body, sender, etc.
        """
        # Validate configuration based on auth method
        if self.auth_method == "oauth2":
            if not all([self.server, self.tenant_id, self.client_id, self.client_secret, self.mailbox]):
                raise ValueError(
                    "OAuth2 email configuration incomplete. "
                    "Please set server, tenant_id, client_id, client_secret, and mailbox in config.yaml"
                )
        else:
            if not all([self.server, self.username, self.password]):
                raise ValueError(
                    "Email server configuration incomplete. "
                    "Please set server, username, and password in config.yaml"
                )
        
        if self.provider != "imap":
            raise ValueError(f"Provider '{self.provider}' not supported. Only 'imap' is currently supported.")
        
        folder_name = folder or self.folder
        
        try:
            if self.auth_method == "oauth2":
                # Get token asynchronously, then run IMAP operations in thread
                access_token = await self._get_oauth2_token()
                emails = await asyncio.to_thread(
                    self._imap_fetch_emails_oauth2,
                    access_token,
                    folder_name,
                    max_results,
                    since_date
                )
            else:
                # Run basic auth IMAP operations in thread
                emails = await asyncio.to_thread(
                    self._imap_fetch_emails,
                    folder_name,
                    max_results,
                    since_date
                )
            
            logger.info(
                f"[green]✅ Successfully retrieved {len(emails)} email(s)[/green]"
            )
            return emails
            
        except Exception as e:
            logger.error(f"[red]❌ Failed to get emails from IMAP server:[/red] {e}")
            raise Exception(f"Failed to get emails from IMAP: {e}")
    
    async def get_recent_emails(
        self,
        max_results: int = 50,
        folder: Optional[str] = None,
        minutes: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get emails that arrived in the last N minutes.
        Uses the configured recent_email_minutes from config.yaml if minutes is not provided.
        
        Args:
            max_results: Maximum number of emails to retrieve (default: 50)
            folder: Mailbox folder to read from (default: configured folder or "INBOX")
            minutes: Time period in minutes to filter emails (default: from config.yaml)
        
        Returns:
            List of email dictionaries that arrived within the specified time period
        """
        # Use provided minutes or fall back to config value
        time_period_minutes = minutes if minutes is not None else self.recent_email_minutes
        
        # Calculate cutoff time (use UTC to avoid timezone issues)
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=time_period_minutes)
        
        # Use IMAP date search to filter at server level (much more efficient)
        # Fetch ALL emails matching the date criteria first (no limit), then apply max_results after filtering
        recent_emails = await self.get_unread_emails(
            max_results=None,  # Fetch all matching emails, don't limit before filtering
            folder=folder,
            since_date=cutoff_time
        )
        
        if not recent_emails:
            logger.info(f"[yellow]No emails found from the last {time_period_minutes} minutes[/yellow]")
            return []
        
        # Additional client-side filtering for precise time comparison
        # (IMAP SINCE search is date-based, so we need to filter by exact time)
        filtered_emails = []
        for email in recent_emails:
            received_datetime_str = email.get("received_datetime")
            if not received_datetime_str:
                # Skip emails without a valid datetime
                logger.debug(f"[dim]Skipping email {email.get('id')} - no received_datetime[/dim]")
                continue
            
            try:
                # Parse the ISO format datetime string
                received_dt = None
                if isinstance(received_datetime_str, str):
                    # Handle ISO format datetime strings
                    if 'T' in received_datetime_str:
                        try:
                            # Try parsing with timezone info first
                            received_dt = datetime.fromisoformat(received_datetime_str.replace('Z', '+00:00'))
                        except ValueError:
                            # If that fails, try without timezone
                            dt_str = received_datetime_str.split('+')[0].split('Z')[0]
                            received_dt = datetime.fromisoformat(dt_str)
                    else:
                        # Try parsing other formats using email.utils
                        from email.utils import parsedate_to_datetime
                        received_dt = parsedate_to_datetime(received_datetime_str)
                else:
                    received_dt = received_datetime_str
                
                # Ensure received_dt is timezone-aware (convert to UTC if naive)
                if received_dt.tzinfo is None:
                    # Assume naive datetime is in UTC
                    received_dt = received_dt.replace(tzinfo=timezone.utc)
                else:
                    # Convert to UTC if it has timezone info
                    received_dt = received_dt.astimezone(timezone.utc)
                
                # Check if email arrived within the time period (precise time comparison)
                if received_dt >= cutoff_time:
                    filtered_emails.append(email)
            except Exception as e:
                logger.warning(
                    f"[yellow]⚠️  Error parsing datetime for email {email.get('id')}:[/yellow] {e}"
                )
                continue
        
        # Apply max_results limit to filtered results (take most recent)
        if max_results is not None and len(filtered_emails) > max_results:
            filtered_emails = filtered_emails[-max_results:]
        
        logger.info(
            f"[green]✅ Found {len(filtered_emails)} email(s) from the last {time_period_minutes} minutes "
            f"(filtered from {len(recent_emails)} emails matching date criteria)[/green]"
        )
        
        return filtered_emails
    
    async def mark_email_as_read(self, email_id: str) -> bool:
        """
        Mark an email as read (not implemented in read-only mode).
        
        Args:
            email_id: Email ID
        
        Returns:
            False (read-only mode does not support marking as read)
        """
        if self.read_only:
            logger.debug(
                f"[dim]Read-only mode: Skipping mark as read for email {email_id}[/dim]"
            )
            return False
        
        # In read-only mode, we don't mark emails as read
        # This method is kept for compatibility but does nothing
        return False
