"""
Database repository for Trackit.

This module provides CRUD operations for habit entries and reports.
It serves as the data access layer for the application.

Author: Trackit Development
"""

import sqlite3
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from contextlib import contextmanager


class HabitRepository:
    """
    Repository for managing habit tracking data in SQLite.

    This class provides methods for:
    - Adding new habit entries
    - Querying entries by date/week/category
    - Managing cached weekly reports
    """

    def __init__(self, db_path: str = "data/trackit.db"):
        """
        Initialize the repository.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path

    @contextmanager
    def _get_connection(self):
        """
        Context manager for database connections.

        Yields:
            sqlite3 connection object

        Example:
            >>> with self._get_connection() as conn:
            ...     cursor = conn.cursor()
            ...     cursor.execute("SELECT * FROM entries")
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def add_entry(
        self,
        raw_input: str,
        category: str,
        mood: str,
        metrics: Dict[str, Any],
        note: Optional[str] = None,
        entry_date: Optional[str] = None
    ) -> int:
        """
        Add a new habit entry to the database.

        Args:
            raw_input: Original user input text
            category: Habit category (运动/学习/睡眠/情绪/饮食/其他)
            mood: Mood label (positive/neutral/negative)
            metrics: Dictionary of quantitative metrics
            note: Optional additional notes
            entry_date: Date string (YYYY-MM-DD), defaults to today

        Returns:
            ID of the inserted entry

        Example:
            >>> repo = HabitRepository()
            >>> entry_id = repo.add_entry(
            ...     raw_input="今天跑了5公里",
            ...     category="运动",
            ...     mood="positive",
            ...     metrics={"distance_km": 5.0}
            ... )
            >>> print(entry_id)
            1
        """
        if entry_date is None:
            entry_date = date.today().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO entries (
                    date, raw_input, category, mood, metrics_json, note
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                entry_date,
                raw_input,
                category,
                mood,
                json.dumps(metrics, ensure_ascii=False),
                note
            ))
            return cursor.lastrowid

    def get_entry_by_id(self, entry_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single entry by ID.

        Args:
            entry_id: The entry ID

        Returns:
            Dictionary containing entry data, or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM entries WHERE id = ?", (entry_id,))
            row = cursor.fetchone()

            if row:
                return self._row_to_dict(row)
            return None

    def get_entries_by_date(
        self,
        entry_date: str,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all entries for a specific date.

        Args:
            entry_date: Date string (YYYY-MM-DD)
            category: Optional filter by category

        Returns:
            List of entry dictionaries

        Example:
            >>> entries = repo.get_entries_by_date("2026-01-10", category="运动")
            >>> len(entries)
            3
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if category:
                cursor.execute("""
                    SELECT * FROM entries
                    WHERE date = ? AND category = ?
                    ORDER BY timestamp ASC
                """, (entry_date, category))
            else:
                cursor.execute("""
                    SELECT * FROM entries
                    WHERE date = ?
                    ORDER BY timestamp ASC
                """, (entry_date,))

            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_entries_by_week(self, week_iso: str) -> List[Dict[str, Any]]:
        """
        Get all entries for a specific ISO week.

        Args:
            week_iso: ISO week string (e.g., "2026-W02")

        Returns:
            List of entry dictionaries

        Example:
            >>> entries = repo.get_entries_by_week("2026-W02")
            >>> print(f"Found {len(entries)} entries")
            Found 15 entries
        """
        # Parse ISO week to get date range
        year, week = map(int, week_iso.split("-W"))
        start_date = datetime.strptime(f"{year}-{week}-1", "%Y-%W-%w").date()
        end_date = start_date + timedelta(days=6)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM entries
                WHERE date >= ? AND date <= ?
                ORDER BY timestamp ASC
            """, (start_date.isoformat(), end_date.isoformat()))

            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_entries_by_date_range(
        self,
        start_date: str,
        end_date: str,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get entries within a date range.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            category: Optional filter by category

        Returns:
            List of entry dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if category:
                cursor.execute("""
                    SELECT * FROM entries
                    WHERE date >= ? AND date <= ? AND category = ?
                    ORDER BY date ASC, timestamp ASC
                """, (start_date, end_date, category))
            else:
                cursor.execute("""
                    SELECT * FROM entries
                    WHERE date >= ? AND date <= ?
                    ORDER BY date ASC, timestamp ASC
                """, (start_date, end_date))

            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_categories(self) -> List[str]:
        """
        Get all unique categories in the database.

        Returns:
            List of category strings
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT category FROM entries
                WHERE category IS NOT NULL
                ORDER BY category
            """)
            return [row[0] for row in cursor.fetchall()]

    def get_entries_by_category(
        self,
        category: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get entries by category, optionally limited.

        Args:
            category: Category to filter by
            limit: Maximum number of entries to return

        Returns:
            List of entry dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if limit:
                cursor.execute("""
                    SELECT * FROM entries
                    WHERE category = ?
                    ORDER BY date DESC, timestamp DESC
                    LIMIT ?
                """, (category, limit))
            else:
                cursor.execute("""
                    SELECT * FROM entries
                    WHERE category = ?
                    ORDER BY date DESC, timestamp DESC
                """, (category,))

            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_entries_by_category_and_date_range(
        self,
        category: str,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        Get entries for a specific category within a date range.

        Args:
            category: Category to filter by
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            List of entry dictionaries
        """
        return self.get_entries_by_date_range(start_date, end_date, category)

    def get_all_entries(
        self,
        limit: Optional[int] = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all entries, optionally limited.

        Args:
            limit: Maximum number of entries to return
            category: Optional category filter

        Returns:
            List of entry dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if category:
                if limit:
                    cursor.execute("""
                        SELECT * FROM entries
                        WHERE category = ?
                        ORDER BY date DESC, timestamp DESC
                        LIMIT ?
                    """, (category, limit))
                else:
                    cursor.execute("""
                        SELECT * FROM entries
                        WHERE category = ?
                        ORDER BY date DESC, timestamp DESC
                    """, (category,))
            else:
                if limit:
                    cursor.execute("""
                        SELECT * FROM entries
                        ORDER BY date DESC, timestamp DESC
                        LIMIT ?
                    """, (limit,))
                else:
                    cursor.execute("""
                        SELECT * FROM entries
                        ORDER BY date DESC, timestamp DESC
                    """)

            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get aggregate statistics for entries.

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            category: Optional category filter

        Returns:
            Dictionary containing statistics
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Build query with filters
            where_clauses = []
            params = []

            if start_date:
                where_clauses.append("date >= ?")
                params.append(start_date)
            if end_date:
                where_clauses.append("date <= ?")
                params.append(end_date)
            if category:
                where_clauses.append("category = ?")
                params.append(category)

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            # Total entries
            cursor.execute(f"""
                SELECT COUNT(*) FROM entries WHERE {where_sql}
            """, params)
            total_count = cursor.fetchone()[0]

            # Count by category
            cursor.execute(f"""
                SELECT category, COUNT(*) as count
                FROM entries
                WHERE {where_sql}
                GROUP BY category
            """, params)
            by_category = {row[0]: row[1] for row in cursor.fetchall()}

            # Mood distribution
            cursor.execute(f"""
                SELECT mood, COUNT(*) as count
                FROM entries
                WHERE {where_sql}
                GROUP BY mood
            """, params)
            mood_dist = {row[0]: row[1] for row in cursor.fetchall()}

            return {
                "total_entries": total_count,
                "by_category": by_category,
                "mood_distribution": mood_dist
            }

    def save_weekly_report(self, week_iso: str, report_data: Dict[str, Any]) -> bool:
        """
        Save or update a cached weekly report.

        Args:
            week_iso: ISO week identifier
            report_data: Dictionary containing the full report

        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO weekly_reports (week_iso, report_json, generated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (week_iso, json.dumps(report_data, ensure_ascii=False)))
                return True
        except Exception as e:
            print(f"Error saving weekly report: {e}")
            return False

    def get_weekly_report(self, week_iso: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a cached weekly report.

        Args:
            week_iso: ISO week identifier

        Returns:
            Report dictionary, or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT report_json, generated_at
                FROM weekly_reports
                WHERE week_iso = ?
            """, (week_iso,))
            row = cursor.fetchone()

            if row:
                return {
                    "data": json.loads(row[0]),
                    "generated_at": row[1],
                    "cached": True
                }
            return None

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """
        Convert a database row to a dictionary.

        Args:
            row: SQLite Row object

        Returns:
            Dictionary representation of the row
        """
        data = dict(row)
        # Parse JSON fields
        if data.get("metrics_json"):
            data["metrics"] = json.loads(data["metrics_json"])
        else:
            data["metrics"] = {}
        return data


# Convenience functions for quick access
def get_repository(db_path: str = "data/trackit.db") -> HabitRepository:
    """
    Get a repository instance.

    Args:
        db_path: Path to the database

    Returns:
        HabitRepository instance
    """
    return HabitRepository(db_path)


if __name__ == "__main__":
    # Test: Create database and add sample entry
    from schema import init_database

    # Initialize database
    schema = init_database()
    print("Database initialized successfully!\n")

    # Create repository
    repo = get_repository()

    # Add test entry
    entry_id = repo.add_entry(
        raw_input="今天跑了5公里，感觉不错",
        category="运动",
        mood="positive",
        metrics={"distance_km": 5.0, "duration_min": 30}
    )

    print(f"Added entry with ID: {entry_id}")

    # Retrieve entry
    entry = repo.get_entry_by_id(entry_id)
    print(f"\nRetrieved entry:")
    for key, value in entry.items():
        print(f"  {key}: {value}")
