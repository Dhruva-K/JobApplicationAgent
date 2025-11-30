"""
Unified LLM client supporting multiple providers.
Supports: Ollama (local), Groq (fast & free), Together AI, OpenAI-compatible APIs.
"""

import logging
import requests
import time
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class LLMClient:
    """Unified client for different LLM providers."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize LLM client with configuration.

        Args:
            config: Dictionary with provider, model_name, api_key, base_url, etc.
        """
        self.provider = config.get("provider", "ollama").lower()
        self.model_name = config.get("model_name", "llama3:8b")
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url", "http://localhost:11434")
        self.timeout = int(config.get("timeout", 60))
        self.temperature = float(config.get("temperature", 0.7))
        self.max_tokens = int(config.get("max_tokens", 2048))

        logger.info(
            f"[LLMClient] Initialized with provider={self.provider}, model={self.model_name}"
        )

    def generate(self, prompt: str, retries: int = 2) -> Optional[str]:
        """
        Generate text from prompt using configured provider.

        Args:
            prompt: Input prompt
            retries: Number of retry attempts

        Returns:
            Generated text or None if failed
        """
        if self.provider == "ollama":
            return self._generate_ollama(prompt, retries)
        elif self.provider == "groq":
            return self._generate_groq(prompt, retries)
        elif self.provider == "together":
            return self._generate_together(prompt, retries)
        elif self.provider == "openai":
            return self._generate_openai_compatible(prompt, retries)
        else:
            logger.error(f"[LLMClient] Unknown provider: {self.provider}")
            return None

    def _generate_ollama(self, prompt: str, retries: int) -> Optional[str]:
        """Generate using local Ollama."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": self.temperature, "top_p": 0.9},
        }

        for attempt in range(retries + 1):
            try:
                response = requests.post(url, json=payload, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "").strip()
            except requests.exceptions.Timeout:
                logger.error(
                    f"[LLMClient] Ollama timeout (attempt {attempt+1}/{retries+1})"
                )
            except requests.exceptions.RequestException as e:
                logger.error(f"[LLMClient] Ollama error: {e}")

            if attempt < retries:
                time.sleep(2 * (attempt + 1))

        return None

    def _generate_groq(self, prompt: str, retries: int) -> Optional[str]:
        """
        Generate using Groq API (fast inference).
        Free tier: 30 requests/min, very fast Llama models.
        Get API key from: https://console.groq.com/keys
        """
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,  # e.g., "llama-3.1-70b-versatile", "mixtral-8x7b-32768"
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        for attempt in range(retries + 1):
            try:
                response = requests.post(
                    url, headers=headers, json=payload, timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            except requests.exceptions.Timeout:
                logger.error(
                    f"[LLMClient] Groq timeout (attempt {attempt+1}/{retries+1})"
                )
            except requests.exceptions.RequestException as e:
                logger.error(f"[LLMClient] Groq error: {e}")
                # Check for rate limit or auth errors
                if hasattr(e, "response") and e.response is not None:
                    logger.error(f"Response: {e.response.text}")
                    # Handle rate limit with adaptive backoff
                    if e.response.status_code == 429:
                        try:
                            error_data = e.response.json()
                            error_msg = error_data.get("error", {}).get("message", "")
                            # Extract wait time from error message (e.g., "try again in 3.78s")
                            import re

                            wait_match = re.search(r"try again in ([\d.]+)s", error_msg)
                            if wait_match:
                                wait_time = (
                                    float(wait_match.group(1)) + 0.5
                                )  # Add buffer
                                logger.info(
                                    f"[LLMClient] Rate limited. Waiting {wait_time}s..."
                                )
                                time.sleep(wait_time)
                                continue
                            # Fallback: wait based on attempt
                            wait_time = 5 * (attempt + 1)
                            logger.info(
                                f"[LLMClient] Rate limited. Waiting {wait_time}s..."
                            )
                            time.sleep(wait_time)
                            continue
                        except Exception:
                            pass

            if attempt < retries:
                time.sleep(2 * (attempt + 1))

        return None

    def _generate_together(self, prompt: str, retries: int) -> Optional[str]:
        """
        Generate using Together AI API.
        Free tier available with credits.
        Get API key from: https://api.together.xyz/settings/api-keys
        """
        url = "https://api.together.xyz/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,  # e.g., "meta-llama/Llama-3-70b-chat-hf"
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        for attempt in range(retries + 1):
            try:
                response = requests.post(
                    url, headers=headers, json=payload, timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            except requests.exceptions.Timeout:
                logger.error(
                    f"[LLMClient] Together timeout (attempt {attempt+1}/{retries+1})"
                )
            except requests.exceptions.RequestException as e:
                logger.error(f"[LLMClient] Together error: {e}")

            if attempt < retries:
                time.sleep(2 * (attempt + 1))

        return None

    def _generate_openai_compatible(self, prompt: str, retries: int) -> Optional[str]:
        """
        Generate using any OpenAI-compatible API.
        Works with OpenAI, Azure OpenAI, or compatible endpoints.
        """
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        for attempt in range(retries + 1):
            try:
                response = requests.post(
                    url, headers=headers, json=payload, timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            except requests.exceptions.Timeout:
                logger.error(
                    f"[LLMClient] OpenAI timeout (attempt {attempt+1}/{retries+1})"
                )
            except requests.exceptions.RequestException as e:
                logger.error(f"[LLMClient] OpenAI error: {e}")

            if attempt < retries:
                time.sleep(2 * (attempt + 1))

        return None

    def is_available(self) -> bool:
        """
        Quick health check to verify LLM service is reachable.

        Returns:
            True if service is available
        """
        try:
            if self.provider == "ollama":
                version_url = f"{self.base_url}/api/version"
                response = requests.get(version_url, timeout=5)
                return response.ok
            elif self.provider in ["groq", "together", "openai"]:
                # For API services, check if API key is set (format validation)
                if not self.api_key or len(self.api_key.strip()) < 10:
                    logger.error(
                        f"[LLMClient] {self.provider} API key missing or too short"
                    )
                    return False
                logger.info(
                    f"[LLMClient] {self.provider} API key present, assuming available"
                )
                return True
            return False
        except Exception as e:
            logger.error(f"[LLMClient] Availability check failed: {e}")
            return False
