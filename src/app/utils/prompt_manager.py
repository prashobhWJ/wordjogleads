"""
Prompt Manager for loading and managing prompts from YAML files
"""
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from app.utils.logging import get_logger

logger = get_logger(__name__)


class PromptManager:
    """
    Manages prompts loaded from YAML files with versioning support.
    """
    
    def __init__(self, prompts_file: Optional[str] = None):
        """
        Initialize the prompt manager.
        
        Args:
            prompts_file: Path to prompts.yaml file. If None, looks for prompts.yaml in:
                         1. Current directory
                         2. Project root
        """
        if prompts_file is None:
            # Try current directory first
            current_dir = Path.cwd() / "prompts.yaml"
            if current_dir.exists():
                prompts_file = str(current_dir)
            else:
                # Try project root (assuming we're in src/app/utils/)
                project_root = Path(__file__).parent.parent.parent.parent / "prompts.yaml"
                if project_root.exists():
                    prompts_file = str(project_root)
                else:
                    raise FileNotFoundError(
                        "prompts.yaml not found. Please create prompts.yaml in the project root."
                    )
        
        self.prompts_file = Path(prompts_file)
        if not self.prompts_file.exists():
            raise FileNotFoundError(f"Prompts file not found: {prompts_file}")
        
        self._prompts_data: Optional[Dict[str, Any]] = None
        self._load_prompts()
    
    def _load_prompts(self) -> None:
        """Load prompts from YAML file"""
        try:
            with open(self.prompts_file, "r") as f:
                self._prompts_data = yaml.safe_load(f)
            
            if self._prompts_data is None:
                raise ValueError("Prompts file is empty or invalid")
            
            logger.info(f"[green]✅ Loaded prompts from:[/green] {self.prompts_file}")
        except Exception as e:
            logger.error(f"[red]❌ Failed to load prompts:[/red] {e}")
            raise
    
    def get_prompt(
        self,
        category: str,
        version: Optional[str] = None,
        default_versions: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Get a prompt by category and version.
        
        Args:
            category: Prompt category (e.g., "system_assistant", "text_summarization")
            version: Specific version to use (e.g., "v1", "v2"). If None, uses default version.
            default_versions: Dictionary of default versions per category. If None, uses defaults from YAML.
        
        Returns:
            Dictionary containing the prompt data (system, user_template, etc.)
        
        Raises:
            KeyError: If category or version not found
        """
        if self._prompts_data is None:
            self._load_prompts()
        
        # Get default versions
        if default_versions is None:
            default_versions = self._prompts_data.get("default_versions", {})
        
        # Determine version to use
        if version is None:
            version = default_versions.get(category, "v1")
        
        # Get prompt
        prompts = self._prompts_data.get("prompts", {})
        if category not in prompts:
            raise KeyError(f"Prompt category '{category}' not found")
        
        category_prompts = prompts[category]
        if version not in category_prompts:
            available_versions = list(category_prompts.keys())
            raise KeyError(
                f"Version '{version}' not found for category '{category}'. "
                f"Available versions: {available_versions}"
            )
        
        prompt_data = category_prompts[version].copy()
        prompt_data["version"] = version
        prompt_data["category"] = category
        
        return prompt_data
    
    def get_system_prompt(
        self,
        category: str,
        version: Optional[str] = None,
        default_versions: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Get only the system prompt for a category.
        
        Args:
            category: Prompt category
            version: Specific version to use
            default_versions: Dictionary of default versions per category
        
        Returns:
            System prompt string
        """
        prompt_data = self.get_prompt(category, version, default_versions)
        return prompt_data.get("system", "")
    
    def get_user_template(
        self,
        category: str,
        version: Optional[str] = None,
        default_versions: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Get the user template for a category.
        
        Args:
            category: Prompt category
            version: Specific version to use
            default_versions: Dictionary of default versions per category
        
        Returns:
            User template string or None if not available
        """
        prompt_data = self.get_prompt(category, version, default_versions)
        return prompt_data.get("user_template")
    
    def format_user_prompt(
        self,
        category: str,
        **kwargs
    ) -> str:
        """
        Get and format a user prompt template with provided variables.
        
        Args:
            category: Prompt category
            **kwargs: Variables to substitute in the template
        
        Returns:
            Formatted user prompt string
        
        Raises:
            KeyError: If template not found or required variables missing
        """
        template = self.get_user_template(category)
        if template is None:
            raise KeyError(f"No user template found for category '{category}'")
        
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise KeyError(f"Missing required variable in template: {e}")
    
    def list_categories(self) -> list:
        """List all available prompt categories"""
        if self._prompts_data is None:
            self._load_prompts()
        
        prompts = self._prompts_data.get("prompts", {})
        return list(prompts.keys())
    
    def list_versions(self, category: str) -> list:
        """List all available versions for a category"""
        if self._prompts_data is None:
            self._load_prompts()
        
        prompts = self._prompts_data.get("prompts", {})
        if category not in prompts:
            raise KeyError(f"Prompt category '{category}' not found")
        
        return list(prompts[category].keys())


# Global prompt manager instance (lazy loaded)
_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager(prompts_file: Optional[str] = None) -> PromptManager:
    """
    Get the global prompt manager instance.
    
    Args:
        prompts_file: Path to prompts.yaml file (only used on first call)
    
    Returns:
        PromptManager instance
    """
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager(prompts_file)
    return _prompt_manager
