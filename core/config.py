"""
Configuration management for the Job Application Agent.
"""

import os
import yaml
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Manages application configuration from YAML and environment variables."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize configuration.
        
        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._override_with_env()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        return {}
    
    def _override_with_env(self):
        """Override config values with environment variables."""
        # Neo4j
        if os.getenv("NEO4J_URI"):
            self.config.setdefault("neo4j", {})["uri"] = os.getenv("NEO4J_URI")
        if os.getenv("NEO4J_USER"):
            self.config.setdefault("neo4j", {})["user"] = os.getenv("NEO4J_USER")
        if os.getenv("NEO4J_PASSWORD"):
            self.config.setdefault("neo4j", {})["password"] = os.getenv("NEO4J_PASSWORD")
        if os.getenv("NEO4J_DATABASE"):
            self.config.setdefault("neo4j", {})["database"] = os.getenv("NEO4J_DATABASE")
        
        # LLM
        if os.getenv("LLM_PROVIDER"):
            self.config.setdefault("llm", {})["provider"] = os.getenv("LLM_PROVIDER")
        if os.getenv("LLM_MODEL_NAME"):
            self.config.setdefault("llm", {})["model_name"] = os.getenv("LLM_MODEL_NAME")
        if os.getenv("LLM_BASE_URL"):
            self.config.setdefault("llm", {})["base_url"] = os.getenv("LLM_BASE_URL")
        if os.getenv("GROQ_API_KEY"):
            self.config.setdefault("llm", {})["api_key"] = os.getenv("GROQ_API_KEY")
        
        # Job APIs
        if os.getenv("JSEARCH_API_KEY"):
            self.config.setdefault("job_apis", {}).setdefault("jsearch", {})["api_key"] = os.getenv("JSEARCH_API_KEY")
        if os.getenv("REMOTIVE_API_KEY"):
            self.config.setdefault("job_apis", {}).setdefault("remotive", {})["api_key"] = os.getenv("REMOTIVE_API_KEY")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated key path.
        
        Args:
            key_path: Dot-separated path (e.g., "neo4j.uri")
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key_path.split('.')
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def get_neo4j_config(self) -> Dict[str, str]:
        """Get Neo4j configuration."""
        return {
            "uri": self.get("neo4j.uri", "bolt://localhost:7687"),
            "user": self.get("neo4j.user", "neo4j"),
            "password": self.get("neo4j.password", "password"),
            "database": self.get("neo4j.database", "neo4j"),
        }
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration."""
        return {
            "provider": self.get("llm.provider", "groq"),
            "model_name": self.get("llm.model_name", "llama-3.3-70b-versatile"),
            "base_url": self.get("llm.base_url", "http://localhost:11434"),
            "api_key": self.get("llm.api_key"),
            "temperature": self.get("llm.temperature", 0.7),
            "max_tokens": self.get("llm.max_tokens", 2048),
        }
    
    def get_job_api_config(self, api_name: str) -> Dict[str, str]:
        """Get job API configuration.
        
        Args:
            api_name: Name of the API ("jsearch" or "remotive")
            
        Returns:
            API configuration dictionary
        """
        return self.get(f"job_apis.{api_name}", {})

