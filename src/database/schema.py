"""
Database schema definitions for Trackit.

This module defines the SQLite database schema used for storing
habit tracking entries and weekly reports.

Tables:
- entries: Stores daily habit records with metadata
- weekly_reports: Caches generated weekly reports

Author: Trackit Development
"""

import sqlite3
from typing import Dict, Any
from datetime import datetime


class DatabaseSchema:
    """Database schema manager for Trackit."""

    def __init__(self, db_path: str = "data/trackit.db"):
        """
        Initialize the database schema.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path

    def create_schema(self) -> None:
        """
        Create all tables and indexes in the database.

        This method creates:
        1. entries table - stores daily habit records
        2. weekly_reports table - caches generated reports
        3. Indexes for common queries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create entries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                date DATE NOT NULL,
                raw_input TEXT NOT NULL,
                category VARCHAR(50),
                mood VARCHAR(20),
                metrics_json TEXT,
                note TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create weekly_reports table for caching
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weekly_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_iso VARCHAR(10) UNIQUE,
                report_json TEXT NOT NULL,
                generated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for common queries
        # Index on date for time-based queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entries_date
            ON entries(date)
        """)

        # Index on category for filtering by habit type
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entries_category
            ON entries(category)
        """)

        # Index on mood for emotional analysis
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entries_mood
            ON entries(mood)
        """)

        # Index on week_iso for fast report lookup
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_reports_week
            ON weekly_reports(week_iso)
        """)

        conn.commit()
        conn.close()

        print(f"✓ Database schema created at {self.db_path}")

    def get_schema_info(self) -> Dict[str, Any]:
        """
        Get information about the database schema.

        Returns:
            Dictionary containing schema information
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get table info
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        # Get indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]

        conn.close()

        return {
            "database": self.db_path,
            "tables": tables,
            "indexes": indexes,
            "created_at": datetime.now().isoformat()
        }


def init_database(db_path: str = "data/trackit.db") -> DatabaseSchema:
    """
    Initialize the Trackit database.

    This is a convenience function that creates the database
    and all necessary tables.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        DatabaseSchema instance

    Example:
        >>> schema = init_database()
        ✓ Database schema created at data/trackit.db
    """
    import os
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    schema = DatabaseSchema(db_path)
    schema.create_schema()
    return schema


if __name__ == "__main__":
    # Test: Create database
    schema = init_database()
    info = schema.get_schema_info()
    print("\nDatabase Schema Info:")
    for key, value in info.items():
        print(f"  {key}: {value}")
