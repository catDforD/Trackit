"""
Claude API client for Trackit.

This module provides a robust wrapper around the Anthropic Claude API
with retry logic, error handling, and cost tracking.

Author: Trackit Development
"""

import time
import json
from typing import Dict, Any, List, Optional, Callable
from anthropic import Anthropic
from anthropic.types import Message

from ..config.settings import settings


class LLMClient:
    """
    Wrapper for Claude API with enhanced error handling and cost tracking.

    Features:
    - Automatic retry with exponential backoff
    - Token counting and cost estimation
    - JSON response validation
    - Request/response logging in debug mode

    Example:
        >>> client = LLMClient()
        >>> response = client.call_with_retry(
        ...     messages=[{"role": "user", "content": "Hello"}],
        ...     model=settings.MODEL_EXTRACTION
        ... )
        >>> print(response.content)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        max_retries: Optional[int] = None,
        retry_delay: Optional[float] = None
    ):
        """
        Initialize the LLM client.

        Args:
            api_key: Anthropic API key (defaults to settings)
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries (seconds)
        """
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.max_retries = max_retries or settings.MAX_RETRIES
        self.retry_delay = retry_delay or settings.RETRY_DELAY

        self.client = Anthropic(api_key=self.api_key)

        # Track usage statistics
        self.total_tokens_used = 0
        self.total_cost = 0.0
        self.total_calls = 0

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
                response = self.client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=messages
                )

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

    def _extract_response_data(self, response: Message, model: str) -> Dict[str, Any]:
        """
        Extract relevant data from API response.

        Args:
            response: Raw API response object
            model: Model name for cost calculation

        Returns:
            Dictionary with response data
        """
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

    print("Testing LLM Client...")
    print("=" * 60)

    # Note: This will fail if ANTHROPIC_API_KEY is not set
    try:
        client = LLMClient()

        # Simple test call
        prompt = Prompts.get_extraction_prompt("今天跑了5公里")
        response = client.call_with_retry(
            messages=[{"role": "user", "content": prompt}],
            model=settings.MODEL_EXTRACTION
        )

        print("\nResponse:")
        print(response["content"])
        print(f"\nTokens: {response['total_tokens']}")
        print(f"Cost: ${response['cost']:.4f}")

        print("\n" + "=" * 60)
        print("Usage Statistics:")
        print(client.get_usage_stats())

    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Make sure ANTHROPIC_API_KEY is set in .env file")
    except Exception as e:
        print(f"Error: {e}")
