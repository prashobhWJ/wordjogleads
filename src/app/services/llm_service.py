"""
LLM Service for OpenAI-compatible API interactions
"""
import httpx
from typing import Dict, Any, Optional, List, AsyncGenerator
from app.core.config import settings
from app.utils.logging import get_logger
from app.utils.prompt_manager import get_prompt_manager

logger = get_logger(__name__)


class LLMService:
    """
    Service for interacting with OpenAI-compatible LLM APIs.
    Supports standard chat completions endpoint format.
    Can use prompts from YAML files with versioning support.
    """
    
    def __init__(self):
        self.base_url = settings.llm.base_url.rstrip('/')
        self.api_key = settings.llm.api_key
        self.default_model = settings.llm.model
        self.timeout = settings.llm.timeout
        self.default_max_tokens = settings.llm.max_tokens
        self.default_temperature = settings.llm.temperature
        self.default_stream = settings.llm.stream
        self.verify_ssl = settings.llm.verify_ssl
        
        # Initialize prompt manager if prompts file is configured
        self._prompt_manager = None
        try:
            self._prompt_manager = get_prompt_manager(settings.llm.prompts_file)
            self._prompt_versions = settings.llm.prompt_versions or {}
        except FileNotFoundError:
            logger.warning("[yellow]⚠️  Prompts file not found. Prompt-based methods will not be available.[/yellow]")
            self._prompt_versions = {}
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Get request headers with authentication.
        
        Returns:
            Headers dictionary with Content-Type and Authorization
        """
        headers = {
            "Content-Type": "application/json",
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        return headers
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: Optional[bool] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a chat completion request to the LLM API.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
                     Example: [{"role": "user", "content": "Hello!"}]
            model: Model to use (defaults to configured model)
            temperature: Sampling temperature (0.0-2.0, defaults to configured value)
            max_tokens: Maximum tokens in response (defaults to configured value)
            stream: Whether to stream the response (defaults to configured value)
            **kwargs: Additional parameters to pass to the API
        
        Returns:
            Dictionary containing the API response
        
        Raises:
            httpx.HTTPError: If the request fails
        """
        url = f"{self.base_url}/chat/completions"
        headers = self._get_headers()
        
        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.default_temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.default_max_tokens,
            "stream": stream if stream is not None else self.default_stream,
            **kwargs
        }
        
        try:
            logger.debug(f"[cyan]Sending chat completion request to LLM:[/cyan] {url}")
            logger.debug(f"[dim]Model:[/dim] {payload['model']}")
            logger.debug(f"[dim]Messages:[/dim] {len(messages)} message(s)")
            
            async with httpx.AsyncClient(
                timeout=self.timeout,
                verify=self.verify_ssl
            ) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers
                )
                
                logger.debug(f"[dim]Response status:[/dim] {response.status_code}")
                
                # Raise for status to catch errors
                response.raise_for_status()
                
                result = response.json()
                logger.info(
                    f"[green]✅ Successfully received LLM response:[/green] "
                    f"[cyan]{payload['model']}[/cyan]"
                )
                return result
                
        except httpx.HTTPStatusError as e:
            error_detail = "Unknown error"
            try:
                if e.response.text:
                    error_detail = e.response.text
            except:
                pass
            
            logger.error(
                f"[red]❌ Failed to get LLM response:[/red] "
                f"[yellow]{e.response.status_code}[/yellow] - {error_detail}"
            )
            logger.error(f"[dim]Request URL:[/dim] {url}")
            logger.error(f"[dim]Request payload:[/dim] {payload}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"[red]❌ HTTP error calling LLM API:[/red] {str(e)}")
            raise
        except Exception as e:
            logger.error(f"[red]❌ Unexpected error calling LLM API:[/red] {str(e)}")
            raise
    
    async def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Send a streaming chat completion request to the LLM API.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            model: Model to use (defaults to configured model)
            temperature: Sampling temperature (0.0-2.0, defaults to configured value)
            max_tokens: Maximum tokens in response (defaults to configured value)
            **kwargs: Additional parameters to pass to the API
        
        Yields:
            String chunks from the streaming response
        
        Raises:
            httpx.HTTPError: If the request fails
        """
        url = f"{self.base_url}/chat/completions"
        headers = self._get_headers()
        
        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.default_temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.default_max_tokens,
            "stream": True,
            **kwargs
        }
        
        try:
            logger.debug(f"[cyan]Sending streaming chat completion request to LLM:[/cyan] {url}")
            logger.debug(f"[dim]Model:[/dim] {payload['model']}")
            
            async with httpx.AsyncClient(
                timeout=self.timeout,
                verify=self.verify_ssl
            ) as client:
                async with client.stream(
                    "POST",
                    url,
                    json=payload,
                    headers=headers
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line:
                            # OpenAI streaming format: "data: {...}\n\n"
                            if line.startswith("data: "):
                                data_str = line[6:]  # Remove "data: " prefix
                                if data_str.strip() == "[DONE]":
                                    break
                                yield data_str
                            
        except httpx.HTTPStatusError as e:
            error_detail = "Unknown error"
            try:
                if e.response.text:
                    error_detail = e.response.text
            except:
                pass
            
            logger.error(
                f"[red]❌ Failed to stream LLM response:[/red] "
                f"[yellow]{e.response.status_code}[/yellow] - {error_detail}"
            )
            raise
        except httpx.HTTPError as e:
            logger.error(f"[red]❌ HTTP error streaming from LLM API:[/red] {str(e)}")
            raise
        except Exception as e:
            logger.error(f"[red]❌ Unexpected error streaming from LLM API:[/red] {str(e)}")
            raise
    
    async def simple_prompt(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Send a simple prompt and get the response text.
        Convenience method that handles message formatting.
        
        Args:
            prompt: User prompt/question
            system_prompt: Optional system prompt for context
            model: Model to use (defaults to configured model)
            **kwargs: Additional parameters to pass to the API
        
        Returns:
            Response text from the LLM
        
        Raises:
            httpx.HTTPError: If the request fails
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        response = await self.chat_completion(messages=messages, model=model, **kwargs)
        
        # Extract the response text from the API response
        if "choices" in response and len(response["choices"]) > 0:
            return response["choices"][0]["message"]["content"]
        else:
            raise ValueError("Invalid response format from LLM API")
    
    # ==================== Prompt-based methods (using YAML prompts) ====================
    
    
    async def match_lead_to_sales_agent(
        self,
        lead_data: Dict[str, Any],
        sales_agents: List[Dict[str, Any]],
        version: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Match a lead to the best sales agent using the sales_agent_matching prompt category.
        
        Args:
            lead_data: Lead information (dict or Lead model instance)
            sales_agents: List of available sales agents with their details
            version: Specific prompt version to use (defaults to configured version)
            model: Model to use (defaults to configured model)
            **kwargs: Additional parameters to pass to the API
        
        Returns:
            Dictionary containing selected agent and analysis
        
        Raises:
            RuntimeError: If prompt manager not initialized
            httpx.HTTPError: If the request fails
            ValueError: If response format is invalid
        """
        if self._prompt_manager is None:
            raise RuntimeError("Prompt manager not initialized. Check prompts.yaml file.")
        
        prompt_data = self._prompt_manager.get_prompt(
            category="sales_agent_matching",
            version=version,
            default_versions=self._prompt_versions
        )
        
        system_prompt = prompt_data.get("system", "")
        user_template = prompt_data.get("user_template", "")
        
        # Load sales agent context if available
        agent_context = ""
        try:
            context_prompt_data = self._prompt_manager.get_prompt(
                category="sales_agent_context",
                version=None,  # Use default version
                default_versions=self._prompt_versions
            )
            agent_context = context_prompt_data.get("context", "")
        except (KeyError, RuntimeError) as e:
            logger.debug(f"[dim]Sales agent context not available:[/dim] {e}")
            # Continue without context if not available
        
        # Format lead data
        if hasattr(lead_data, '__dict__'):
            # SQLAlchemy model instance
            lead_dict = {
                "lead_id": getattr(lead_data, 'lead_id', None),
                "full_name": getattr(lead_data, 'full_name', None),
                "first_name": getattr(lead_data, 'first_name', None),
                "last_name": getattr(lead_data, 'last_name', None),
                "email": getattr(lead_data, 'email', None),
                "phone": getattr(lead_data, 'phone', None),
                "city": getattr(lead_data, 'city', None),
                "state_province": getattr(lead_data, 'state_province', None),
                "country": getattr(lead_data, 'country', None),
                "vehicle_type": getattr(lead_data, 'vehicle_type', None),
                "current_credit": getattr(lead_data, 'current_credit', None),
                "employment_status": getattr(lead_data, 'employment_status', None),
                "company_name": getattr(lead_data, 'company_name', None),
                "monthly_salary_min": float(getattr(lead_data, 'monthly_salary_min', 0) or 0),
                "monthly_salary_max": float(getattr(lead_data, 'monthly_salary_max', 0) or 0),
            }
        elif isinstance(lead_data, dict):
            lead_dict = lead_data
        else:
            lead_dict = {"lead_info": str(lead_data)}
        
        # Format lead info as readable text
        import json
        lead_info_lines = []
        lead_info_lines.append(f"Lead ID: {lead_dict.get('lead_id', 'N/A')}")
        # Build full name
        full_name = lead_dict.get('full_name')
        if not full_name:
            first = lead_dict.get('first_name', '')
            last = lead_dict.get('last_name', '')
            full_name = f"{first} {last}".strip() or 'N/A'
        lead_info_lines.append(f"Name: {full_name}")
        lead_info_lines.append(f"Email: {lead_dict.get('email', 'N/A')}")
        lead_info_lines.append(f"Phone: {lead_dict.get('phone', 'N/A')}")
        lead_info_lines.append(f"Location: {lead_dict.get('city', '')}, {lead_dict.get('state_province', '')}, {lead_dict.get('country', '')}")
        if lead_dict.get('vehicle_type'):
            lead_info_lines.append(f"Vehicle Interest: {lead_dict.get('vehicle_type')}")
        if lead_dict.get('current_credit'):
            lead_info_lines.append(f"Credit Status: {lead_dict.get('current_credit')}")
        if lead_dict.get('employment_status'):
            lead_info_lines.append(f"Employment: {lead_dict.get('employment_status')}")
        if lead_dict.get('company_name'):
            lead_info_lines.append(f"Company: {lead_dict.get('company_name')}")
        if lead_dict.get('monthly_salary_min') or lead_dict.get('monthly_salary_max'):
            salary_range = f"${lead_dict.get('monthly_salary_min', 0):,.0f}"
            if lead_dict.get('monthly_salary_max'):
                salary_range += f" - ${lead_dict.get('monthly_salary_max', 0):,.0f}"
            lead_info_lines.append(f"Salary Range: {salary_range}/month")
        
        lead_info_str = "\n".join(lead_info_lines)
        
        # Format sales agents info
        agents_lines = []
        for idx, agent in enumerate(sales_agents, 1):
            agent_lines = [f"Agent #{idx}:"]
            agent_lines.append(f"  ID: {agent.get('id', agent.get('agent_id', 'N/A'))}")
            agent_lines.append(f"  Name: {agent.get('name', agent.get('agent_name', 'N/A'))}")
            if agent.get('specialization'):
                agent_lines.append(f"  Specialization: {agent.get('specialization')}")
            if agent.get('expertise'):
                agent_lines.append(f"  Expertise: {agent.get('expertise')}")
            if agent.get('experience_years'):
                agent_lines.append(f"  Experience: {agent.get('experience_years')} years")
            if agent.get('location') or agent.get('territory'):
                agent_lines.append(f"  Location/Territory: {agent.get('location') or agent.get('territory', 'N/A')}")
            if agent.get('current_workload'):
                agent_lines.append(f"  Current Workload: {agent.get('current_workload')} active leads")
            if agent.get('success_rate'):
                agent_lines.append(f"  Success Rate: {agent.get('success_rate')}%")
            if agent.get('vehicle_types'):
                agent_lines.append(f"  Vehicle Types: {', '.join(agent.get('vehicle_types', []))}")
            if agent.get('communication_style'):
                agent_lines.append(f"  Communication Style: {agent.get('communication_style')}")
            agents_lines.append("\n".join(agent_lines))
        
        sales_agents_str = "\n\n".join(agents_lines)
        
        # Format user prompt with context
        try:
            # Try with agent_context first (for updated prompts)
            if agent_context and "{agent_context}" in user_template:
                user_prompt = user_template.format(
                    agent_context=agent_context,
                    lead_info=lead_info_str,
                    sales_agents=sales_agents_str
                )
            else:
                # Fallback for prompts without context variable
                user_prompt = user_template.format(
                    lead_info=lead_info_str,
                    sales_agents=sales_agents_str
                )
        except KeyError as e:
            logger.warning(f"[yellow]Template variable missing:[/yellow] {e}. Using fallback format.")
            # If context is available but template doesn't have the variable, prepend it
            if agent_context:
                user_prompt = f"{agent_context}\n\n{lead_info_str}\n\n{sales_agents_str}"
            else:
                user_prompt = f"{lead_info_str}\n\n{sales_agents_str}"
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})
        
        logger.info(
            f"[cyan]Matching lead {lead_dict.get('lead_id', 'N/A')} to sales agent...[/cyan] "
            f"[dim]Evaluating {len(sales_agents)} agents[/dim]"
        )
        
        response = await self.chat_completion(messages=messages, model=model, **kwargs)
        
        if "choices" in response and len(response["choices"]) > 0:
            response_text = response["choices"][0]["message"]["content"]
            
            # Parse JSON response
            import json
            try:
                # Try to extract JSON from response (in case there's extra text)
                response_text = response_text.strip()
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                if response_text.startswith("```"):
                    response_text = response_text[3:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]
                response_text = response_text.strip()
                
                result = json.loads(response_text)
                
                # Log the selected sales person
                selected_agent_name = result.get("selected_agent_name", result.get("selected_agent_id", "Unknown"))
                selected_agent_id = result.get("selected_agent_id", "N/A")
                confidence = result.get("confidence_score", "N/A")
                reasoning = result.get("reasoning", "No reasoning provided")
                
                logger.info(
                    f"[green]✅ Selected Sales Agent:[/green] "
                    f"[bold cyan]{selected_agent_name}[/bold cyan] "
                    f"(ID: {selected_agent_id}, Confidence: {confidence}/10)"
                )
                logger.info(f"[dim]Reasoning:[/dim] {reasoning}")
                
                return result
            except json.JSONDecodeError as e:
                logger.error(f"[red]❌ Failed to parse LLM response as JSON:[/red] {e}")
                logger.error(f"[dim]Response text:[/dim] {response_text}")
                raise ValueError(f"Invalid JSON response from LLM: {e}")
        else:
            raise ValueError("Invalid response format from LLM API")
    
    def get_available_prompts(self) -> Dict[str, List[str]]:
        """
        Get list of available prompt categories and their versions.
        
        Returns:
            Dictionary mapping category names to lists of available versions
        """
        if self._prompt_manager is None:
            return {}
        
        categories = {}
        for category in self._prompt_manager.list_categories():
            categories[category] = self._prompt_manager.list_versions(category)
        
        return categories