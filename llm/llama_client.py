"""
LLM client wrapper for Ollama and vLLM.
"""

import json
import logging
import requests
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from a prompt."""
        pass
    
    @abstractmethod
    def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate and parse JSON response."""
        pass


class OllamaClient(LLMClient):
    """Ollama client for local LLM inference."""
    
    def __init__(
        self,
        model_name: str = "llama3:8b",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.7,
        max_tokens: int = 2048
    ):
        """Initialize Ollama client.
        
        Args:
            model_name: Name of the model (e.g., "llama3:8b")
            base_url: Ollama API base URL
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        """
        self.model_name = model_name
        self.base_url = base_url.rstrip('/')
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_url = f"{self.base_url}/api/generate"
    
    def generate(self, prompt: str, temperature: Optional[float] = None, max_tokens: Optional[int] = None) -> str:
        """Generate text from a prompt.
        
        Args:
            prompt: Input prompt
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            
        Returns:
            Generated text
        """
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature if temperature is not None else self.temperature,
                "num_predict": max_tokens if max_tokens is not None else self.max_tokens,
            }
        }
        
        try:
            response = requests.post(self.api_url, json=payload, timeout=120)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "").strip()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Ollama API: {e}")
            raise
    
    def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate and parse JSON response.
        
        Args:
            prompt: Input prompt (should request JSON output)
            **kwargs: Additional arguments for generate()
            
        Returns:
            Parsed JSON dictionary
        """
        response = self.generate(prompt, **kwargs)
        
        # Try to extract JSON from response
        try:
            # Look for JSON in the response
            response = response.strip()
            
            # Try to find JSON object/array
            start_idx = response.find('{')
            if start_idx == -1:
                start_idx = response.find('[')
            
            if start_idx != -1:
                end_idx = response.rfind('}') + 1
                if end_idx == 0:
                    end_idx = response.rfind(']') + 1
                if end_idx > start_idx:
                    json_str = response[start_idx:end_idx]
                    return json.loads(json_str)
            
            # If no JSON found, try parsing entire response
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from response: {e}")
            logger.debug(f"Response was: {response[:200]}")
            # Return a fallback structure
            return {"error": "Failed to parse JSON", "raw_response": response}
    
    def generate_batch(self, prompts: List[str], **kwargs) -> List[str]:
        """Generate responses for multiple prompts.
        
        Args:
            prompts: List of input prompts
            **kwargs: Additional arguments for generate()
            
        Returns:
            List of generated texts
        """
        return [self.generate(prompt, **kwargs) for prompt in prompts]
    
    def is_available(self) -> bool:
        """Check if Ollama service is available.
        
        Returns:
            True if service is reachable
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False


class VLLMClient(LLMClient):
    """vLLM client for high-performance inference (future implementation)."""
    
    def __init__(
        self,
        model_name: str = "llama3-8b",
        base_url: str = "http://localhost:8000",
        temperature: float = 0.7,
        max_tokens: int = 2048
    ):
        """Initialize vLLM client.
        
        Args:
            model_name: Name of the model
            base_url: vLLM API base URL
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        """
        self.model_name = model_name
        self.base_url = base_url.rstrip('/')
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_url = f"{self.base_url}/v1/completions"
    
    def generate(self, prompt: str, temperature: Optional[float] = None, max_tokens: Optional[int] = None) -> str:
        """Generate text from a prompt.
        
        Args:
            prompt: Input prompt
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            
        Returns:
            Generated text
        """
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
        }
        
        try:
            response = requests.post(self.api_url, json=payload, timeout=120)
            response.raise_for_status()
            result = response.json()
            return result.get("choices", [{}])[0].get("text", "").strip()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling vLLM API: {e}")
            raise
    
    def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate and parse JSON response."""
        response = self.generate(prompt, **kwargs)
        
        try:
            response = response.strip()
            start_idx = response.find('{')
            if start_idx == -1:
                start_idx = response.find('[')
            
            if start_idx != -1:
                end_idx = response.rfind('}') + 1
                if end_idx == 0:
                    end_idx = response.rfind(']') + 1
                if end_idx > start_idx:
                    json_str = response[start_idx:end_idx]
                    return json.loads(json_str)
            
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from response: {e}")
            return {"error": "Failed to parse JSON", "raw_response": response}
    
    def is_available(self) -> bool:
        """Check if vLLM service is available."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False


def create_llm_client(config: Dict[str, Any]) -> LLMClient:
    """Factory function to create LLM client based on configuration.
    
    Args:
        config: LLM configuration dictionary
        
    Returns:
        LLMClient instance
    """
    provider = config.get("provider", "ollama").lower()
    
    if provider == "ollama":
        return OllamaClient(
            model_name=config.get("model_name", "llama3:8b"),
            base_url=config.get("base_url", "http://localhost:11434"),
            temperature=config.get("temperature", 0.7),
            max_tokens=config.get("max_tokens", 2048)
        )
    elif provider == "vllm":
        return VLLMClient(
            model_name=config.get("model_name", "llama3-8b"),
            base_url=config.get("base_url", "http://localhost:8000"),
            temperature=config.get("temperature", 0.7),
            max_tokens=config.get("max_tokens", 2048)
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

