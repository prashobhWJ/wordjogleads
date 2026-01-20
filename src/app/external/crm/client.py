"""
CRM REST API client
"""
import httpx
from typing import Dict, Any, Optional
from app.core.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class CRMClient:
    """
    Client for interacting with CRM REST API.
    Handles authentication, requests, and error handling.
    """
    
    def __init__(self):
        self.base_url = settings.crm.base_url
        self.api_key = settings.crm.api_key
        self.api_token = settings.crm.api_token
        self.timeout = settings.crm.timeout
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Get request headers with authentication.
        Matches the curl format: Content-Type and Authorization Bearer token.
        """
        headers = {
            "Content-Type": "application/json",
        }
        
        # Twenty CRM uses Bearer token authentication
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        elif self.api_key:
            # Fallback to API key if token not available
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        return headers
    
    async def create_record(
        self,
        endpoint: str,
        data: Dict[str, Any],
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a record in the CRM system (Twenty CRM).
        Matches the curl format: POST to /rest/people with Bearer token.
        
        Args:
            endpoint: API endpoint path (e.g., "rest/people")
            data: Data to send in the request body
            params: Optional query parameters (e.g., {"upsert": True})
            **kwargs: Additional parameters for httpx request
        
        Returns:
            Dict containing the response data
        
        Raises:
            httpx.HTTPError: If the request fails
        """
        # Build URL - ensure no double slashes
        base = self.base_url.rstrip('/')
        endpoint_clean = endpoint.lstrip('/')
        url = f"{base}/{endpoint_clean}"
        
        headers = self._get_headers()
        
        # Merge params with kwargs params if provided
        request_params = params or {}
        if 'params' in kwargs:
            request_params.update(kwargs.pop('params'))
        
        try:
            # Log the request for debugging
            logger.debug(f"[cyan]Creating record in CRM:[/cyan] {url}")
            logger.debug(f"[dim]Request data:[/dim] {data}")
            if request_params:
                logger.debug(f"[dim]Query params:[/dim] {request_params}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=data,
                    headers=headers,
                    params=request_params,
                    **kwargs
                )
                
                # Log response status
                logger.debug(f"[dim]Response status:[/dim] {response.status_code}")
                
                # Raise for status to catch errors
                response.raise_for_status()
                
                result = response.json()
                logger.info(
                    f"[green]✅ Successfully created record in CRM:[/green] "
                    f"[cyan]{endpoint}[/cyan]"
                )
                return result
                
        except httpx.HTTPStatusError as e:
            # Get error details from response
            error_detail = "Unknown error"
            try:
                if e.response.text:
                    error_detail = e.response.text
            except:
                pass
            
            logger.error(
                f"[red]❌ Failed to create record in CRM:[/red] "
                f"[yellow]{e.response.status_code}[/yellow] - {error_detail}"
            )
            logger.error(f"[dim]Request URL:[/dim] {url}")
            logger.error(f"[dim]Request data:[/dim] {data}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"[red]❌ HTTP error creating record in CRM:[/red] {str(e)}")
            raise
        except Exception as e:
            logger.error(f"[red]❌ Unexpected error creating record in CRM:[/red] {str(e)}")
            raise
    
    async def get_record(
        self,
        endpoint: str,
        record_id: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get a record from the CRM system.
        
        Args:
            endpoint: API endpoint path
            record_id: Optional record ID to append to endpoint
            params: Optional query parameters for filtering/searching
            **kwargs: Additional parameters for httpx request
        
        Returns:
            Dict containing the response data
        """
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        if record_id:
            url = f"{url}/{record_id}"
        
        headers = self._get_headers()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    url,
                    headers=headers,
                    params=params,
                    **kwargs
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get record from CRM: {e}")
            raise
    
    async def update_record(
        self,
        endpoint: str,
        record_id: str,
        data: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Update a record in the CRM system.
        
        Args:
            endpoint: API endpoint path
            record_id: Record ID to update
            data: Data to send in the request body
            **kwargs: Additional parameters for httpx request
        
        Returns:
            Dict containing the response data
        """
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}/{record_id}"
        headers = self._get_headers()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(
                    url,
                    json=data,
                    headers=headers,
                    **kwargs
                )
                response.raise_for_status()
                logger.info(f"[green]Successfully updated record in CRM:[/green] [cyan]{endpoint}/{record_id}[/cyan]")
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to update record in CRM: {e}")
            raise
    
    async def delete_record(
        self,
        endpoint: str,
        record_id: str,
        **kwargs
    ) -> bool:
        """
        Delete a record from the CRM system.
        
        Args:
            endpoint: API endpoint path
            record_id: Record ID to delete
            **kwargs: Additional parameters for httpx request
        
        Returns:
            True if successful
        """
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}/{record_id}"
        headers = self._get_headers()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(
                    url,
                    headers=headers,
                    **kwargs
                )
                response.raise_for_status()
                logger.info(f"[green]Successfully deleted record from CRM:[/green] [cyan]{endpoint}/{record_id}[/cyan]")
                return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to delete record from CRM: {e}")
            raise
