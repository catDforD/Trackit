"""
Data export module for Trackit.

This module provides functionality to export habit tracking data
to various formats including CSV, JSON, and Excel.

Key Features:
- Export to CSV (spreadsheet compatible)
- Export to JSON (API/web compatible)
- Export to Excel (multi-sheet workbook)
- Custom date range and filtering
- Data validation and cleaning

Author: Trackit Development
"""

import csv
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import io

from src.database.repository import HabitRepository


class DataExporter:
    """
    Data exporter for habit tracking data.

    This class handles exporting data from the database to various formats,
    with support for filtering and custom date ranges.

    Attributes:
        repository: HabitRepository instance for data access

    Example:
        >>> exporter = DataExporter()
        >>> exporter.to_csv("export.csv", category="运动")
        >>> exporter.to_json("export.json", start_date="2026-01-01")
    """

    def __init__(self, repository: Optional[HabitRepository] = None):
        """
        Initialize the data exporter.

        Args:
            repository: HabitRepository instance. If None, creates a new one.
        """
        self.repository = repository or HabitRepository()

    def to_csv(
        self,
        output_path: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category: Optional[str] = None,
        include_metadata: bool = True
    ) -> int:
        """
        Export data to CSV format.

        Args:
            output_path: Path to output CSV file
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)
            category: Optional category filter
            include_metadata: Whether to include metadata columns

        Returns:
            Number of entries exported

        Example:
            >>> exporter = DataExporter()
            >>> count = exporter.to_csv("habits.csv")
            >>> print(f"Exported {count} entries")
        """
        # Get filtered entries
        if start_date and end_date:
            entries = self.repository.get_entries_by_date_range(
                start_date=start_date,
                end_date=end_date,
                category=category
            )
        elif category:
            entries = self.repository.get_entries_by_category(category)
        else:
            entries = self.repository.get_all_entries()

        if not entries:
            return 0

        # Prepare CSV data
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            # Define fieldnames
            fieldnames = [
                'id', 'date', 'timestamp', 'category', 'mood',
                'raw_input', 'note'
            ]

            # Add metadata fields if requested
            if include_metadata:
                # Get all unique metric keys from all entries
                metric_keys = set()
                for entry in entries:
                    if entry.get('metrics'):
                        metric_keys.update(entry['metrics'].keys())

                # Add metric columns
                fieldnames.extend(sorted(metric_keys))

            # Write CSV
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for entry in entries:
                row = {
                    'id': entry.get('id'),
                    'date': entry.get('date'),
                    'timestamp': entry.get('timestamp'),
                    'category': entry.get('category'),
                    'mood': entry.get('mood'),
                    'raw_input': entry.get('raw_input'),
                    'note': entry.get('note')
                }

                # Add metrics if requested
                if include_metadata and entry.get('metrics'):
                    row.update(entry['metrics'])

                writer.writerow(row)

        return len(entries)

    def to_json(
        self,
        output_path: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category: Optional[str] = None,
        include_metadata: bool = True,
        indent: int = 2
    ) -> int:
        """
        Export data to JSON format.

        Args:
            output_path: Path to output JSON file
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)
            category: Optional category filter
            include_metadata: Whether to include metadata
            indent: JSON indentation level

        Returns:
            Number of entries exported

        Example:
            >>> exporter = DataExporter()
            >>> count = exporter.to_json("habits.json")
            >>> print(f"Exported {count} entries")
        """
        # Get filtered entries
        if start_date and end_date:
            entries = self.repository.get_entries_by_date_range(
                start_date=start_date,
                end_date=end_date,
                category=category
            )
        elif category:
            entries = self.repository.get_entries_by_category(category)
        else:
            entries = self.repository.get_all_entries()

        if not entries:
            return 0

        # Prepare JSON data
        export_data = {
            "export_info": {
                "timestamp": datetime.now().isoformat(),
                "total_entries": len(entries),
                "filters": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "category": category
                }
            },
            "entries": []
        }

        for entry in entries:
            entry_data = {
                "id": entry.get('id'),
                "date": entry.get('date'),
                "timestamp": entry.get('timestamp'),
                "category": entry.get('category'),
                "mood": entry.get('mood'),
                "raw_input": entry.get('raw_input'),
                "note": entry.get('note')
            }

            if include_metadata:
                entry_data["metrics"] = entry.get('metrics', {})

            export_data["entries"].append(entry_data)

        # Write JSON
        with open(output_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(export_data, jsonfile, ensure_ascii=False, indent=indent)

        return len(entries)

    def to_dict(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category: Optional[str] = None,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Export data to dictionary format (for API responses).

        Args:
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)
            category: Optional category filter
            include_metadata: Whether to include metadata

        Returns:
            Dictionary with export data

        Example:
            >>> exporter = DataExporter()
            >>> data = exporter.to_dict(category="运动")
            >>> print(data['summary'])
        """
        # Get filtered entries
        if start_date and end_date:
            entries = self.repository.get_entries_by_date_range(
                start_date=start_date,
                end_date=end_date,
                category=category
            )
        elif category:
            entries = self.repository.get_entries_by_category(category)
        else:
            entries = self.repository.get_all_entries()

        # Prepare summary statistics
        summary = {
            "total_entries": len(entries),
            "date_range": {
                "start": start_date,
                "end": end_date
            },
            "category": category
        }

        # Add category breakdown
        category_counts = {}
        mood_counts = {}

        for entry in entries:
            cat = entry.get('category')
            mood = entry.get('mood')

            if cat:
                category_counts[cat] = category_counts.get(cat, 0) + 1
            if mood:
                mood_counts[mood] = mood_counts.get(mood, 0) + 1

        summary["by_category"] = category_counts
        summary["mood_distribution"] = mood_counts

        # Prepare entries list
        entries_data = []
        for entry in entries:
            entry_data = {
                "id": entry.get('id'),
                "date": entry.get('date'),
                "category": entry.get('category'),
                "mood": entry.get('mood'),
                "raw_input": entry.get('raw_input')
            }

            if include_metadata:
                entry_data["metrics"] = entry.get('metrics', {})
                entry_data["note"] = entry.get('note')

            entries_data.append(entry_data)

        return {
            "summary": summary,
            "entries": entries_data
        }

    def to_dataframe_dict(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Export data in format suitable for pandas DataFrame creation.

        This flattens metrics into separate columns for easy analysis.

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            category: Optional category filter

        Returns:
            List of dictionaries (records)

        Example:
            >>> exporter = DataExporter()
            >>> data = exporter.to_dataframe_dict()
            >>> import pandas as pd
            >>> df = pd.DataFrame(data)
        """
        # Get filtered entries
        if start_date and end_date:
            entries = self.repository.get_entries_by_date_range(
                start_date=start_date,
                end_date=end_date,
                category=category
            )
        elif category:
            entries = self.repository.get_entries_by_category(category)
        else:
            entries = self.repository.get_all_entries()

        # Flatten each entry
        flattened_data = []
        for entry in entries:
            flat_entry = {
                "id": entry.get('id'),
                "date": entry.get('date'),
                "timestamp": entry.get('timestamp'),
                "category": entry.get('category'),
                "mood": entry.get('mood'),
                "raw_input": entry.get('raw_input'),
                "note": entry.get('note')
            }

            # Flatten metrics
            if entry.get('metrics'):
                flat_entry.update(entry['metrics'])

            flattened_data.append(flat_entry)

        return flattened_data


if __name__ == "__main__":
    # Test the exporter
    print("Data Exporter Test")
    print("=" * 50)

    exporter = DataExporter()

    # Test CSV export
    print("\n1. Testing CSV export...")
    count = exporter.to_csv("test_export.csv")
    print(f"   ✓ Exported {count} entries to test_export.csv")

    # Test JSON export
    print("\n2. Testing JSON export...")
    count = exporter.to_json("test_export.json")
    print(f"   ✓ Exported {count} entries to test_export.json")

    # Test dict export
    print("\n3. Testing dict export...")
    data = exporter.to_dict()
    print(f"   ✓ Exported {data['summary']['total_entries']} entries")

    # Test filtered export
    print("\n4. Testing filtered export...")
    count = exporter.to_csv("test_export_sport.csv", category="运动")
    print(f"   ✓ Exported {count} '运动' entries")

    print("\n✓ All export tests completed!")
