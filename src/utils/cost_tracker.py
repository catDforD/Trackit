"""
Cost tracking and analysis for Trackit.

This module tracks API usage and costs for different operations:
- Recording habits (HabitExtractor)
- Querying habits (IntentClassifier)
- Report generation

Author: Trackit Development
"""

import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class APICallRecord:
    """Record of a single API call."""
    timestamp: str
    operation: str  # "extract", "classify", "generate_report"
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    cached: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class CostTracker:
    """
    Track and analyze API usage costs.

    Example:
        >>> tracker = CostTracker()
        >>> tracker.log_call("extract", "claude-3-5-haiku-20241022", 100, 50, cached=False)
        >>> tracker.get_total_cost()
        0.000235
        >>> tracker.generate_report()
    """

    # Pricing (USD per 1M tokens) as of 2025
    PRICING = {
        "claude-3-5-haiku-20241022": {"input": 1.0, "output": 5.0},
        "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4o": {"input": 2.50, "output": 10.0},
    }

    # Token estimates for common operations
    TOKEN_ESTIMATES = {
        "extract": {"input": 200, "output": 150},  # Habit extraction
        "classify": {"input": 150, "output": 50},  # Intent classification
        "generate_report": {"input": 1000, "output": 1500},  # Report generation
    }

    def __init__(self, log_file: Optional[str] = None):
        """
        Initialize cost tracker.

        Args:
            log_file: Optional path to log file for persistence
        """
        self.records: List[APICallRecord] = []
        self.log_file = log_file or "data/api_costs.json"

        # Load existing records if file exists
        self._load_from_file()

    def log_call(
        self,
        operation: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cached: bool = False
    ) -> float:
        """
        Log an API call and calculate its cost.

        Args:
            operation: Type of operation (extract, classify, generate_report)
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cached: Whether this call was served from cache

        Returns:
            Cost in USD
        """
        # Calculate cost
        total_tokens = input_tokens + output_tokens
        cost = self._calculate_cost(model, input_tokens, output_tokens)

        # Create record
        record = APICallRecord(
            timestamp=datetime.now().isoformat(),
            operation=operation,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_usd=cost,
            cached=cached
        )

        self.records.append(record)
        self._save_to_file()

        return cost

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost for a model call.

        Args:
            model: Model name
            input_tokens: Input tokens
            output_tokens: Output tokens

        Returns:
            Cost in USD
        """
        if model not in self.PRICING:
            # Default to Haiku pricing if model not found
            pricing = self.PRICING["claude-3-5-haiku-20241022"]
        else:
            pricing = self.PRICING[model]

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    def estimate_operation_cost(
        self,
        operation: str,
        model: str = "claude-3-5-haiku-20241022"
    ) -> Dict[str, Any]:
        """
        Estimate cost for an operation type.

        Args:
            operation: Type of operation
            model: Model to use

        Returns:
            Dictionary with cost estimate
        """
        if operation not in self.TOKEN_ESTIMATES:
            return {"error": f"Unknown operation: {operation}"}

        tokens = self.TOKEN_ESTIMATES[operation]
        cost = self._calculate_cost(
            model,
            tokens["input"],
            tokens["output"]
        )

        return {
            "operation": operation,
            "model": model,
            "estimated_input_tokens": tokens["input"],
            "estimated_output_tokens": tokens["output"],
            "estimated_total_tokens": tokens["input"] + tokens["output"],
            "estimated_cost_usd": cost
        }

    def get_total_cost(self) -> float:
        """Get total cost of all logged calls."""
        return sum(record.cost_usd for record in self.records)

    def get_operation_costs(self) -> Dict[str, Dict[str, Any]]:
        """Get cost breakdown by operation type."""
        breakdown = {}

        for record in self.records:
            if record.operation not in breakdown:
                breakdown[record.operation] = {
                    "calls": 0,
                    "total_tokens": 0,
                    "total_cost": 0.0,
                    "cached_calls": 0
                }

            breakdown[record.operation]["calls"] += 1
            breakdown[record.operation]["total_tokens"] += record.total_tokens
            breakdown[record.operation]["total_cost"] += record.cost_usd
            if record.cached:
                breakdown[record.operation]["cached_calls"] += 1

        return breakdown

    def get_model_costs(self) -> Dict[str, Dict[str, Any]]:
        """Get cost breakdown by model."""
        breakdown = {}

        for record in self.records:
            if record.model not in breakdown:
                breakdown[record.model] = {
                    "calls": 0,
                    "total_tokens": 0,
                    "total_cost": 0.0
                }

            breakdown[record.model]["calls"] += 1
            breakdown[record.model]["total_tokens"] += record.total_tokens
            breakdown[record.model]["total_cost"] += record.cost_usd

        return breakdown

    def get_cache_savings(self) -> Dict[str, Any]:
        """Calculate savings from caching."""
        cached_calls = [r for r in self.records if r.cached]
        total_cached_cost = sum(r.cost_usd for r in cached_calls if not r.cached)

        # Estimate what cached calls would have cost
        cached_operation_costs = {}
        for record in cached_calls:
            if record.operation not in cached_operation_costs:
                cached_operation_costs[record.operation] = []
            cached_operation_costs[record.operation].append(record.cost_usd if not record.cached else 0)

        # Calculate actual savings
        # (Cached calls have minimal cost, so we save the full API cost)
        non_cached_calls = [r for r in self.records if not r.cached]
        avg_cost_per_call = sum(r.cost_usd for r in non_cached_calls) / len(non_cached_calls) if non_cached_calls else 0

        estimated_saved = len(cached_calls) * avg_cost_per_call

        return {
            "cached_calls": len(cached_calls),
            "total_calls": len(self.records),
            "cache_hit_rate": len(cached_calls) / len(self.records) if self.records else 0,
            "estimated_savings_usd": estimated_saved
        }

    def get_daily_costs(self) -> Dict[str, float]:
        """Get daily cost breakdown."""
        daily = {}

        for record in self.records:
            # Extract date from timestamp
            date = record.timestamp.split("T")[0]
            if date not in daily:
                daily[date] = 0.0
            daily[date] += record.cost_usd

        return daily

    def generate_report(self) -> str:
        """Generate a comprehensive cost report."""
        if not self.records:
            return "No API calls recorded yet."

        total_cost = self.get_total_cost()
        operation_costs = self.get_operation_costs()
        model_costs = self.get_model_costs()
        cache_savings = self.get_cache_savings()
        daily_costs = self.get_daily_costs()

        report = []
        report.append("\n" + "="*70)
        report.append("TRACKIT API COST ANALYSIS REPORT")
        report.append("="*70)

        # Summary
        report.append(f"\n📊 Total Cost: ${total_cost:.4f} USD")
        report.append(f"📞 Total Calls: {len(self.records)}")
        report.append(f"💰 Average Cost per Call: ${total_cost/len(self.records):.6f}")

        # By operation
        report.append("\n📋 Cost by Operation:")
        report.append("-" * 70)
        for op, data in operation_costs.items():
            cache_rate = data["cached_calls"] / data["calls"] if data["calls"] > 0 else 0
            report.append(
                f"  {op}: ${data['total_cost']:.4f} "
                f"({data['calls']} calls, "
                f"{cache_rate:.0%} cached)"
            )

        # By model
        report.append("\n🤖 Cost by Model:")
        report.append("-" * 70)
        for model, data in model_costs.items():
            report.append(
                f"  {model}: ${data['total_cost']:.4f} "
                f"({data['calls']} calls, "
                f"{data['total_tokens']:,} tokens)"
            )

        # Cache savings
        report.append("\n⚡ Cache Performance:")
        report.append("-" * 70)
        report.append(f"  Cache hit rate: {cache_savings['cache_hit_rate']:.1%}")
        report.append(f"  Cached calls: {cache_savings['cached_calls']}")
        report.append(f"  Estimated savings: ${cache_savings['estimated_savings_usd']:.4f}")

        # Daily breakdown
        if daily_costs:
            report.append("\n📅 Daily Costs:")
            report.append("-" * 70)
            for date, cost in sorted(daily_costs.items()):
                report.append(f"  {date}: ${cost:.4f}")

        # Recommendations
        report.append("\n💡 Cost Optimization Recommendations:")
        report.append("-" * 70)

        if cache_savings["cache_hit_rate"] < 0.3:
            report.append("  ⚠️  Low cache hit rate. Consider enabling cache.")

        total_tokens = sum(r.total_tokens for r in self.records)
        avg_tokens_per_call = total_tokens / len(self.records) if self.records else 0

        if avg_tokens_per_call > 500:
            report.append("  ⚠️  High token usage. Consider prompt optimization.")

        # Check if using expensive models for simple tasks
        for model, data in model_costs.items():
            if "sonnet" in model.lower() or "gpt-4o" in model.lower():
                simple_ops = [r for r in self.records if r.model == model and r.operation == "classify"]
                if len(simple_ops) > 10:
                    report.append(f"  ⚠️  Using {model} for {len(simple_ops)} classifications.")
                    report.append("     Consider using Haiku/mini for classification.")

        report.append("\n" + "="*70)

        return "\n".join(report)

    def export_to_csv(self, filename: str) -> None:
        """Export cost data to CSV file."""
        import csv

        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp", "operation", "model",
                "input_tokens", "output_tokens",
                "total_tokens", "cost_usd", "cached"
            ])

            for record in self.records:
                writer.writerow([
                    record.timestamp,
                    record.operation,
                    record.model,
                    record.input_tokens,
                    record.output_tokens,
                    record.total_tokens,
                    f"{record.cost_usd:.6f}",
                    record.cached
                ])

    def _load_from_file(self) -> None:
        """Load records from file."""
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    data = json.load(f)
                    self.records = [APICallRecord(**r) for r in data]
            except Exception as e:
                print(f"Warning: Could not load cost log: {e}")

    def _save_to_file(self) -> None:
        """Save records to file."""
        # Ensure directory exists
        Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)

        with open(self.log_file, 'w') as f:
            data = [record.to_dict() for record in self.records]
            json.dump(data, f, indent=2)

    def clear(self) -> None:
        """Clear all records."""
        self.records.clear()
        self._save_to_file()


# Global cost tracker instance
_cost_tracker = None


def get_cost_tracker() -> CostTracker:
    """Get the global cost tracker instance."""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker


if __name__ == "__main__":
    # Test: Generate sample cost data and report
    tracker = CostTracker()

    # Simulate some API calls
    models_and_costs = [
        ("claude-3-5-haiku-20241022", 200, 150),
        ("claude-3-5-haiku-20241022", 200, 150),
        ("claude-3-5-sonnet-20241022", 1000, 1500),
    ]

    for i, (model, input_t, output_t) in enumerate(models_and_costs):
        tracker.log_call(
            operation="extract" if i < 2 else "generate_report",
            model=model,
            input_tokens=input_t,
            output_tokens=output_t,
            cached=(i == 1)  # Second call is cached
        )

    print(tracker.generate_report())
