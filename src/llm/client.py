"""
Unified LLM client for Trackit.

This module provides a unified interface for both Anthropic and OpenAI APIs
with automatic retry logic, error handling, and cost tracking.

Author: Trackit Development
"""

import time
import json
from typing import Dict, Any, List, Optional, Callable
from abc import ABC, abstractmethod
from ..config.settings import settings

try:
    from anthropic import Anthropic
    from anthropic.types import Message
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class BaseLLMClient(ABC):
    """
    Abstract base class for LLM clients.

    Defines the common interface that all LLM provider clients must implement.
    """

    def __init__(
        self,
        api_key: str,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize the LLM client.

        Args:
            api_key: API key for the LLM service
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries (seconds)
        """
        self.api_key = api_key
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Track usage statistics
        self.total_tokens_used = 0
        self.total_cost = 0.0
        self.total_calls = 0

    @abstractmethod
    def _call_api(
        self,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> Any:
        """
        Make the actual API call.

        Args:
            messages: List of message dictionaries
            model: Model name
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            Raw API response
        """
        pass

    @abstractmethod
    def _extract_response_data(self, response: Any, model: str) -> Dict[str, Any]:
        """
        Extract relevant data from API response.

        Args:
            response: Raw API response
            model: Model name for cost calculation

        Returns:
            Dictionary with response data
        """
        pass


    def call_with_retry(
        self,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        expected_format: Optional[Dict[str, Any]] = None,
        response_processor: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Call LLM with automatic retry on failure.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model name to use
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            expected_format: Optional JSON schema for validation
            response_processor: Optional function to process response

        Returns:
            Dictionary containing:
                - content: Response text
                - input_tokens: Input token count
                - output_tokens: Output token count
                - cost: Estimated cost in USD
                - raw: Raw API response

        Raises:
            Exception: If all retry attempts fail
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                if settings.DEBUG:
                    print(f"[DEBUG] LLM call (attempt {attempt + 1}/{self.max_retries})")
                    print(f"[DEBUG] Model: {model}")
                    print(f"[DEBUG] Messages: {messages[:1]}...")  # First message only

                # Make API call
                response = self._call_api(messages, model, max_tokens, temperature)

                # Extract response data
                result = self._extract_response_data(response, model)

                # Update statistics
                self.total_calls += 1
                self.total_tokens_used += result["input_tokens"] + result["output_tokens"]
                self.total_cost += result["cost"]

                # Validate if expected format provided
                if expected_format:
                    self._validate_json_response(result["content"], expected_format)

                # Apply custom processor if provided
                if response_processor:
                    result["processed"] = response_processor(result["content"])

                if settings.DEBUG:
                    print(f"[DEBUG] Response tokens: {result['output_tokens']}")
                    print(f"[DEBUG] Cost: ${result['cost']:.4f}")

                return result

            except Exception as e:
                last_exception = e
                print(f"Attempt {attempt + 1} failed: {str(e)}")

                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    wait_time = self.retry_delay * (2 ** attempt)
                    print(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)

        # All retries failed
        raise Exception(f"LLM call failed after {self.max_retries} attempts: {str(last_exception)}")

    def _validate_json_response(
        self,
        content: str,
        expected_format: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate JSON response against expected schema.

        Args:
            content: Response text (should be JSON)
            expected_format: Expected JSON schema

        Returns:
            Parsed JSON object

        Raises:
            ValueError: If content is not valid JSON or doesn't match schema
        """
        try:
            # Try to extract JSON from markdown code blocks
            if "```json" in content:
                # Extract from ```json...```
                start = content.find("```json") + 7
                end = content.find("```", start)
                json_str = content[start:end].strip()
            elif "```" in content:
                # Extract from ```...```
                start = content.find("```") + 3
                end = content.find("```", start)
                json_str = content[start:end].strip()
            else:
                # Try parsing entire content as JSON
                json_str = content.strip()

            data = json.loads(json_str)

            # Basic validation: check if keys exist
            for key in expected_format.keys():
                if key not in data:
                    raise ValueError(f"Missing required key: {key}")

            return data

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in response: {e}\nContent: {content}")

    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics since client initialization.

        Returns:
            Dictionary with usage statistics
        """
        return {
            "total_calls": self.total_calls,
            "total_tokens": self.total_tokens_used,
            "total_cost_usd": round(self.total_cost, 4),
            "avg_cost_per_call": round(self.total_cost / max(self.total_calls, 1), 4),
            "avg_tokens_per_call": round(self.total_tokens_used / max(self.total_calls, 1), 0)
        }

    def reset_stats(self) -> None:
        """Reset usage statistics."""
        self.total_tokens_used = 0
        self.total_cost = 0.0
        self.total_calls = 0


class AnthropicClient(BaseLLMClient):
    """
    Anthropic Claude API client implementation.

    Provides a wrapper around the Anthropic Claude API with enhanced error handling.
    """

    def __init__(
        self,
        api_key: str,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize the Anthropic client.

        Args:
            api_key: Anthropic API key
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries (seconds)
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "anthropic package is required for AnthropicClient. "
                "Install it with: pip install anthropic"
            )

        super().__init__(api_key, max_retries, retry_delay)
        self.client = Anthropic(api_key=self.api_key)

    def _call_api(
        self,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> Message:
        """Make API call to Anthropic."""
        return self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages
        )

    def _extract_response_data(self, response: Message, model: str) -> Dict[str, Any]:
        """Extract data from Anthropic response."""
        # Get text content
        content = response.content[0].text

        # Get token usage
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        # Calculate cost
        cost = settings.estimate_cost(model, input_tokens, output_tokens)

        return {
            "content": content,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost": cost,
            "model": model,
            "raw": response
        }


class OpenAIClient(BaseLLMClient):
    """
    OpenAI API client implementation.

    Provides a wrapper around the OpenAI API (and compatible APIs) with enhanced error handling.
    Supports custom base_url for using OpenAI-compatible services.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize the OpenAI client.

        Args:
            api_key: OpenAI API key
            base_url: Base URL for the API (can be customized for compatible services)
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries (seconds)
        """
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "openai package is required for OpenAIClient. "
                "Install it with: pip install openai"
            )

        super().__init__(api_key, max_retries, retry_delay)
        self.base_url = base_url
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def _call_api(
        self,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> Any:
        """Make API call to OpenAI."""
        return self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    def _extract_response_data(self, response: Any, model: str) -> Dict[str, Any]:
        """Extract data from OpenAI response."""
        # Get text content
        content = response.choices[0].message.content

        # Get token usage
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens

        # Calculate cost
        cost = settings.estimate_cost(model, input_tokens, output_tokens)

        return {
            "content": content,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost": cost,
            "model": model,
            "raw": response
        }


class LLMClient:
    """
    Unified LLM client that supports multiple providers.

    This factory class creates the appropriate client based on the LLM_PROVIDER setting.
    It provides a consistent interface regardless of the underlying provider.

    Example:
        >>> # Uses provider from settings
        >>> client = LLMClient()
        >>> response = client.call_with_retry(
        ...     messages=[{"role": "user", "content": "Hello"}],
        ...     model="gpt-4o-mini"
        ... )

        >>> # Override provider
        >>> client = LLMClient(provider="openai")
        >>> response = client.call_with_retry(...)
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_retries: Optional[int] = None,
        retry_delay: Optional[float] = None,
    ):
        """
        Initialize the unified LLM client.

        Args:
            provider: LLM provider ("anthropic" or "openai"). Defaults to settings.LLM_PROVIDER
            api_key: API key (defaults to settings)
            base_url: Base URL for OpenAI-compatible APIs (only for OpenAI provider)
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries (seconds)
        """
        self.provider = provider or settings.LLM_PROVIDER
        self.max_retries = max_retries or settings.MAX_RETRIES
        self.retry_delay = retry_delay or settings.RETRY_DELAY

        # Create the appropriate client based on provider
        if self.provider == "anthropic":
            api_key = api_key or settings.ANTHROPIC_API_KEY
            if not api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY is required for Anthropic provider. "
                    "Set it in .env or pass api_key parameter."
                )
            self._client = AnthropicClient(
                api_key=api_key,
                max_retries=self.max_retries,
                retry_delay=self.retry_delay,
            )

        elif self.provider == "openai":
            api_key = api_key or settings.OPENAI_API_KEY
            base_url = base_url or settings.OPENAI_BASE_URL
            if not api_key:
                raise ValueError(
                    "OPENAI_API_KEY is required for OpenAI provider. "
                    "Set it in .env or pass api_key parameter."
                )
            self._client = OpenAIClient(
                api_key=api_key,
                base_url=base_url,
                max_retries=self.max_retries,
                retry_delay=self.retry_delay,
            )

        else:
            raise ValueError(
                f"Unsupported provider: {self.provider}. "
                "Must be 'anthropic' or 'openai'."
            )

    def call_with_retry(
        self,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        expected_format: Optional[Dict[str, Any]] = None,
        response_processor: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Call LLM with automatic retry on failure.

        This method delegates to the underlying provider-specific client.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model name to use
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            expected_format: Optional JSON schema for validation
            response_processor: Optional function to process response

        Returns:
            Dictionary with response data
        """
        return self._client.call_with_retry(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            expected_format=expected_format,
            response_processor=response_processor,
        )

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return self._client.get_usage_stats()

    def reset_stats(self) -> None:
        """Reset usage statistics."""
        self._client.reset_stats()

    @property
    def total_tokens_used(self) -> int:
        """Total tokens used since client initialization."""
        return self._client.total_tokens_used

    @property
    def total_cost(self) -> float:
        """Total cost in USD since client initialization."""
        return self._client.total_cost

    @property
    def total_calls(self) -> int:
        """Total number of API calls since client initialization."""
        return self._client.total_calls


def extract_json_from_response(content: str) -> Dict[str, Any]:
    """
    Extract and parse JSON from LLM response.

    Handles various JSON formats in responses:
    - Plain JSON
    - Markdown code blocks with ```json
    - Markdown code blocks with ```

    Args:
        content: Raw response text

    Returns:
        Parsed JSON object

    Raises:
        ValueError: If JSON cannot be extracted or parsed

    Example:
        >>> response = '{"category": "运动", "mood": "positive"}'
        >>> data = extract_json_from_response(response)
        >>> print(data["category"])
        运动
    """
    try:
        # Try to extract JSON from markdown code blocks
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            json_str = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            json_str = content[start:end].strip()
        else:
            json_str = content.strip()

        return json.loads(json_str)

    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to extract JSON: {e}\nContent: {content}")


if __name__ == "__main__":
    # Test: Basic client functionality
    from ..config.prompts import Prompts

    print("Testing Unified LLM Client...")
    print("=" * 60)

    # Note: This will fail if API keys are not set
    try:
        # Test with Anthropic
        if settings.LLM_PROVIDER == "anthropic" and settings.ANTHROPIC_API_KEY:
            print("\n1. Testing Anthropic Client...")
            client = LLMClient(provider="anthropic")

            prompt = Prompts.get_extraction_prompt("今天跑了5公里")
            response = client.call_with_retry(
                messages=[{"role": "user", "content": prompt}],
                model=settings.MODEL_EXTRACTION
            )

            print("Response:", response["content"][:100])
            print("Tokens:", response['total_tokens'])
            print("Cost:", f"${response['cost']:.4f}")
            print("Usage Stats:", client.get_usage_stats())

        # Test with OpenAI
        elif settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
            print("\n1. Testing OpenAI Client...")
            client = LLMClient(provider="openai")

            prompt = Prompts.get_extraction_prompt("今天跑了5公里")
            response = client.call_with_retry(
                messages=[{"role": "user", "content": prompt}],
                model="gpt-4o"
            )

            print("Response:", response["content"][:100])
            print("Tokens:", response['total_tokens'])
            print("Cost:", f"${response['cost']:.4f}")
            print("Usage Stats:", client.get_usage_stats())

        print("\n" + "=" * 60)
        print("Test completed successfully!")

    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Make sure appropriate API keys are set in .env file")
    except Exception as e:
        print(f"Error: {e}")
