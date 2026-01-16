#!/usr/bin/env python3
"""
Database health check script for ResuBoost AI.

This script monitors database health, performance, and provides recommendations.

Usage:
    python scripts/database_health_check.py
    python scripts/database_health_check.py --detailed
    python scripts/database_health_check.py --json
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


class DatabaseHealthChecker:
    """Database health checker."""

    def __init__(self, db_path: str, db_name: str):
        """
        Initialize health checker.

        Args:
            db_path: Path to database file
            db_name: Database name
        """
        self.db_path = db_path
        self.db_name = db_name
        self.issues = []
        self.warnings = []
        self.recommendations = []

    def check_existence(self) -> bool:
        """Check if database file exists."""
        if not os.path.exists(self.db_path):
            self.issues.append("Database file does not exist")
            return False
        return True

    def check_size(self) -> dict:
        """Check database file size."""
        size_bytes = os.path.getsize(self.db_path)
        size_mb = size_bytes / (1024 * 1024)

        # Warn if database is getting large (>100 MB for SQLite)
        if size_mb > 100:
            self.warnings.append(
                f"Database size is {size_mb:.2f} MB. Consider migrating to PostgreSQL for better performance."
            )

        # Warn if database is very large (>500 MB)
        if size_mb > 500:
            self.issues.append(
                f"Database size is {size_mb:.2f} MB. SQLite performance may degrade. Migration to PostgreSQL strongly recommended."
            )

        return {
            "size_bytes": size_bytes,
            "size_mb": round(size_mb, 2),
            "size_gb": round(size_mb / 1024, 2),
        }

    def check_integrity(self) -> bool:
        """Check database integrity."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()

            conn.close()

            if result and result[0] == "ok":
                return True
            else:
                self.issues.append(f"Integrity check failed: {result}")
                return False

        except Exception as e:
            self.issues.append(f"Integrity check error: {e}")
            return False

    def check_journal_mode(self) -> str:
        """Check and recommend journal mode."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("PRAGMA journal_mode")
            mode = cursor.fetchone()[0]

            conn.close()

            if mode.upper() != "WAL":
                self.recommendations.append(
                    f"Journal mode is '{mode}'. Consider using WAL mode for better concurrency: PRAGMA journal_mode=WAL"
                )

            return mode

        except Exception as e:
            self.warnings.append(f"Could not check journal mode: {e}")
            return "unknown"

    def check_tables(self) -> list:
        """Get list of tables and row counts."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]

            table_info = []

            for table in tables:
                # Get row count
                cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
                row_count = cursor.fetchone()[0]

                # Get approximate size
                cursor.execute(f'SELECT SUM(length(quote())) FROM "{table}"')
                table_size = cursor.fetchone()[0] or 0

                table_info.append({"name": table, "rows": row_count, "size_bytes": table_size})

            conn.close()

            return table_info

        except Exception as e:
            self.warnings.append(f"Could not analyze tables: {e}")
            return []

    def check_indexes(self) -> list:
        """Get list of indexes."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT name, tbl_name
                FROM sqlite_master
                WHERE type='index' AND name NOT LIKE 'sqlite_%'
                ORDER BY tbl_name, name
            """
            )

            indexes = [{"name": row[0], "table": row[1]} for row in cursor.fetchall()]

            conn.close()

            return indexes

        except Exception as e:
            self.warnings.append(f"Could not check indexes: {e}")
            return []

    def check_foreign_keys(self) -> bool:
        """Check if foreign keys are enabled."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("PRAGMA foreign_keys")
            enabled = cursor.fetchone()[0]

            conn.close()

            if not enabled:
                self.warnings.append(
                    "Foreign keys are not enabled. Enable with: PRAGMA foreign_keys=ON"
                )

            return bool(enabled)

        except Exception as e:
            self.warnings.append(f"Could not check foreign keys: {e}")
            return False

    def check_page_size(self) -> int:
        """Check database page size."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]

            conn.close()

            # Recommend larger page size for better performance
            if page_size < 4096:
                self.recommendations.append(
                    f"Page size is {page_size} bytes. Consider using 4096 or 8192 for better performance."
                )

            return page_size

        except Exception as e:
            self.warnings.append(f"Could not check page size: {e}")
            return 0

    def check_vacuum_needed(self) -> bool:
        """Check if VACUUM would be beneficial."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get page count and freelist count
            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]

            cursor.execute("PRAGMA freelist_count")
            freelist_count = cursor.fetchone()[0]

            conn.close()

            # If more than 10% of pages are free, recommend VACUUM
            if page_count > 0 and (freelist_count / page_count) > 0.1:
                self.recommendations.append(
                    f"Database has {freelist_count} free pages ({freelist_count/page_count*100:.1f}% of total). "
                    f"Consider running VACUUM to reclaim space."
                )
                return True

            return False

        except Exception as e:
            self.warnings.append(f"Could not check vacuum status: {e}")
            return False

    def run_full_check(self, detailed: bool = False) -> dict:
        """
        Run full health check.

        Args:
            detailed: Whether to include detailed information

        Returns:
            Dictionary with health check results
        """
        results = {
            "database": self.db_name,
            "path": self.db_path,
            "timestamp": datetime.now().isoformat(),
            "healthy": True,
            "issues": [],
            "warnings": [],
            "recommendations": [],
        }

        # Check existence
        if not self.check_existence():
            results["healthy"] = False
            results["issues"] = self.issues
            return results

        # Check integrity
        integrity_ok = self.check_integrity()
        results["integrity_ok"] = integrity_ok

        if not integrity_ok:
            results["healthy"] = False

        # Check size
        size_info = self.check_size()
        results["size"] = size_info

        # Check journal mode
        journal_mode = self.check_journal_mode()
        results["journal_mode"] = journal_mode

        # Check foreign keys
        foreign_keys_enabled = self.check_foreign_keys()
        results["foreign_keys_enabled"] = foreign_keys_enabled

        # Check page size
        page_size = self.check_page_size()
        results["page_size"] = page_size

        # Check if vacuum needed
        vacuum_needed = self.check_vacuum_needed()
        results["vacuum_recommended"] = vacuum_needed

        # Get tables info if detailed
        if detailed:
            tables = self.check_tables()
            results["tables"] = tables

            indexes = self.check_indexes()
            results["indexes"] = indexes

        # Aggregate issues, warnings, recommendations
        results["issues"] = self.issues
        results["warnings"] = self.warnings
        results["recommendations"] = self.recommendations

        # Set overall health status
        if self.issues:
            results["healthy"] = False
        elif self.warnings:
            results["health_status"] = "warning"
        else:
            results["health_status"] = "good"

        return results


def print_health_report(results: dict, detailed: bool = False):
    """Print health report in human-readable format."""
    print("\n" + "=" * 70)
    print(f"Database: {results['database']}")
    print("=" * 70)

    # Overall status
    if results.get("healthy", False):
        print("✅ Status: HEALTHY")
    else:
        print("❌ Status: ISSUES FOUND")

    print()

    # Basic info
    print(f"📁 Path: {results['path']}")

    if "size" in results:
        size = results["size"]
        print(f"💾 Size: {size['size_bytes']:,} bytes ({size['size_mb']:.2f} MB)")

    if "integrity_ok" in results:
        status = "✅ OK" if results["integrity_ok"] else "❌ FAILED"
        print(f"🔍 Integrity: {status}")

    if "journal_mode" in results:
        print(f"📝 Journal Mode: {results['journal_mode']}")

    if "foreign_keys_enabled" in results:
        status = "✅ Enabled" if results["foreign_keys_enabled"] else "⚠️  Disabled"
        print(f"🔗 Foreign Keys: {status}")

    if "page_size" in results:
        print(f"📄 Page Size: {results['page_size']} bytes")

    # Tables (detailed)
    if detailed and "tables" in results:
        print("\n📊 Tables:")
        for table in results["tables"]:
            size_mb = table["size_bytes"] / (1024 * 1024)
            print(f"   • {table['name']}: {table['rows']:,} rows ({size_mb:.2f} MB)")

    # Indexes (detailed)
    if detailed and "indexes" in results:
        print(f"\n🔖 Indexes: {len(results['indexes'])}")
        for index in results["indexes"]:
            print(f"   • {index['name']} on {index['table']}")

    # Issues
    if results.get("issues"):
        print("\n❌ Issues:")
        for issue in results["issues"]:
            print(f"   • {issue}")

    # Warnings
    if results.get("warnings"):
        print("\n⚠️  Warnings:")
        for warning in results["warnings"]:
            print(f"   • {warning}")

    # Recommendations
    if results.get("recommendations"):
        print("\n💡 Recommendations:")
        for rec in results["recommendations"]:
            print(f"   • {rec}")

    print("\n" + "=" * 70)


def main():
    """Main health check function."""
    parser = argparse.ArgumentParser(description="Check ResuBoost AI database health")
    parser.add_argument(
        "--detailed", action="store_true", help="Show detailed information (tables, indexes, etc.)"
    )
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--database", type=str, help="Check specific database (default: all)")

    args = parser.parse_args()

    # Get list of databases
    data_path = Path(DATA_DIR)

    if not data_path.exists():
        print(f"❌ Data directory not found: {DATA_DIR}")
        return

    databases = []

    if args.database:
        # Check specific database
        db_path = os.path.join(DATA_DIR, f"{args.database}.db")
        if os.path.exists(db_path):
            databases.append((args.database, db_path))
        else:
            print(f"❌ Database not found: {db_path}")
            return
    else:
        # Check all databases
        for db_file in data_path.glob("*.db"):
            databases.append((db_file.stem, str(db_file)))

    if not databases:
        print("⚠️  No databases found")
        return

    # Run health check on each database
    all_results = []

    for db_name, db_path in databases:
        checker = DatabaseHealthChecker(db_path, db_name)
        results = checker.run_full_check(detailed=args.detailed)
        all_results.append(results)

    # Output results
    if args.json:
        # JSON output
        print(json.dumps(all_results, indent=2))
    else:
        # Human-readable output
        print("\n" + "=" * 70)
        print("ResuBoost AI - Database Health Check")
        print("=" * 70)
        print(f"Checked at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        for results in all_results:
            print_health_report(results, detailed=args.detailed)

        # Summary
        healthy_count = sum(1 for r in all_results if r.get("healthy", False))
        total_count = len(all_results)

        print("\n" + "=" * 70)
        print(f"Summary: {healthy_count}/{total_count} database(s) healthy")
        print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Health check interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Health check failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
