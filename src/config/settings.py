"""
Configuration management for Trackit.

This module handles application settings, API keys, and model configurations.
It uses environment variables for sensitive data like API keys.

Author: Trackit Development
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """
    Application settings and configuration.

    This class centralizes all configuration including:
    - API keys for LLM services
    - Model selection (Haiku vs Sonnet for cost optimization)
    - Database paths
    - Application behavior

    Example:
        >>> settings = Settings()
        >>> print(settings.MODEL_EXTRACTION)
        'claude-3-5-haiku-20241022'
    """

    # Application
    APP_NAME: str = os.getenv("APP_NAME", "Trackit")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///data/trackit.db")
    DB_PATH: str = DATABASE_URL.replace("sqlite:///", "")

    # Anthropic Claude API
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Model Selection
    # Cost optimization: Use Haiku for simple tasks, Sonnet for complex ones
    # Haiku: $0.80/$4 per 1M tokens (fast, cost-effective)
    # Sonnet: $3/$15 per 1M tokens (best quality)

    MODEL_EXTRACTION: str = os.getenv(
        "MODEL_EXTRACTION",
        "claude-3-5-haiku-20241022"  # Use Haiku for extraction (cost-effective)
    )

    MODEL_CLASSIFICATION: str = os.getenv(
        "MODEL_CLASSIFICATION",
        "claude-3-5-haiku-20241022"  # Use Haiku for classification
    )

    MODEL_REPORT: str = os.getenv(
        "MODEL_REPORT",
        "claude-3-5-sonnet-20241022"  # Use Sonnet for reports (best quality)
    )

    # Model configurations
    MODEL_CONFIGS: Dict[str, Dict[str, Any]] = {
        "claude-3-5-haiku-20241022": {
            "name": "Claude 3.5 Haiku",
            "max_tokens": 8192,
            "temperature": 0.0,
            "cost_per_input": 0.80,  # per 1M tokens
            "cost_per_output": 4.0,
        },
        "claude-3-5-sonnet-20241022": {
            "name": "Claude 3.5 Sonnet",
            "max_tokens": 8192,
            "temperature": 0.0,
            "cost_per_input": 3.0,
            "cost_per_output": 15.0,
        }
    }

    # LLM Settings
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0  # seconds
    TIMEOUT: int = 60  # seconds

    # Gradio Settings
    GRADIO_SHARE: bool = os.getenv("GRADIO_SHARE", "false").lower() == "true"
    GRADIO_SERVER_PORT: int = int(os.getenv("GRADIO_SERVER_PORT", "7860"))
    GRADIO_SERVER_NAME: str = os.getenv("GRADIO_SERVER_NAME", "127.0.0.1")

    def __init__(self):
        """Initialize settings and validate required configuration."""
        self._validate()

    def _validate(self) -> None:
        """
        Validate that required settings are present.

        Raises:
            ValueError: If required API keys are missing
        """
        if not self.ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY is required! "
                "Please set it in .env file or environment variables."
            )

    def get_model_config(self, model_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific model.

        Args:
            model_name: Name of the model

        Returns:
            Dictionary with model configuration

        Raises:
            ValueError: If model is not recognized
        """
        if model_name not in self.MODEL_CONFIGS:
            raise ValueError(f"Unknown model: {model_name}")
        return self.MODEL_CONFIGS[model_name]

    def estimate_cost(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        Estimate API call cost in USD.

        Args:
            model_name: Model to use
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD

        Example:
            >>> settings = Settings()
            >>> cost = settings.estimate_cost("claude-3-5-haiku-20241022", 1000, 500)
            >>> print(f"Estimated cost: ${cost:.4f}")
            Estimated cost: $0.0028
        """
        config = self.get_model_config(model_name)
        input_cost = (input_tokens / 1_000_000) * config["cost_per_input"]
        output_cost = (output_tokens / 1_000_000) * config["cost_per_output"]
        return input_cost + output_cost

    def __repr__(self) -> str:
        """String representation of settings (hides sensitive data)."""
        return (
            f"Settings(\n"
            f"  APP_NAME={self.APP_NAME},\n"
            f"  DB_PATH={self.DB_PATH},\n"
            f"  MODEL_EXTRACTION={self.MODEL_EXTRACTION},\n"
            f"  MODEL_REPORT={self.MODEL_REPORT},\n"
            f"  API_KEY configured={bool(self.ANTHROPIC_API_KEY)}\n"
            f")"
        )


# Global settings instance
settings = Settings()


if __name__ == "__main__":
    # Test: Display settings
    print("=" * 50)
    print("Trackit Application Settings")
    print("=" * 50)
    print(settings)
    print("\n" + "=" * 50)
    print("Cost Estimation Example")
    print("=" * 50)

    # Example: Estimate cost for different operations
    operations = [
        ("Extraction", settings.MODEL_EXTRACTION, 500, 300),
        ("Classification", settings.MODEL_CLASSIFICATION, 200, 100),
        ("Weekly Report", settings.MODEL_REPORT, 2000, 1000),
    ]

    total_cost = 0
    for name, model, input_t, output_t in operations:
        cost = settings.estimate_cost(model, input_t, output_t)
        total_cost += cost
        print(f"{name}: {input_t} input + {output_t} output tokens = ${cost:.4f}")

    print("-" * 50)
    print(f"Total estimated cost: ${total_cost:.4f}")
