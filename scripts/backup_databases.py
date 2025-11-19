#!/usr/bin/env python3
"""
Automated database backup script for ResuBoost AI.

This script creates backups of all application databases with rotation.
Can be run manually or scheduled via cron.

Usage:
    python scripts/backup_databases.py
    python scripts/backup_databases.py --keep-days 90
    python scripts/backup_databases.py --verify
"""

import os
import sys
import shutil
import sqlite3
import argparse
from datetime import datetime, timedelta
from pathlib import Path


# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backups')
DEFAULT_KEEP_DAYS = 30


def create_backup_dir():
    """Create backup directory if it doesn't exist."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    print(f"✅ Backup directory: {BACKUP_DIR}")


def get_databases():
    """
    Get list of database files to backup.

    Returns:
        List of tuples (db_name, db_path)
    """
    databases = []

    # Find all .db files in data directory
    data_path = Path(DATA_DIR)

    if not data_path.exists():
        print(f"⚠️  Data directory not found: {DATA_DIR}")
        return databases

    for db_file in data_path.glob('*.db'):
        databases.append((db_file.stem, str(db_file)))

    return databases


def verify_database(db_path: str) -> bool:
    """
    Verify database integrity.

    Args:
        db_path: Path to database file

    Returns:
        True if database is valid, False otherwise
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Run integrity check
        cursor.execute('PRAGMA integrity_check')
        result = cursor.fetchone()

        conn.close()

        if result and result[0] == 'ok':
            return True
        else:
            print(f"❌ Integrity check failed for {db_path}: {result}")
            return False

    except Exception as e:
        print(f"❌ Error verifying {db_path}: {e}")
        return False


def backup_database(db_name: str, db_path: str, verify: bool = False) -> bool:
    """
    Backup a single database.

    Args:
        db_name: Database name (without extension)
        db_path: Path to database file
        verify: Whether to verify backup after creation

    Returns:
        True if backup successful, False otherwise
    """
    try:
        # Check if source database exists
        if not os.path.exists(db_path):
            print(f"⚠️  Database not found: {db_path}")
            return False

        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"{db_name}_{timestamp}.db"
        backup_path = os.path.join(BACKUP_DIR, backup_filename)

        # Verify source database before backup
        if verify and not verify_database(db_path):
            print(f"❌ Source database verification failed: {db_name}")
            return False

        # Create backup using SQLite backup API (safer than file copy)
        print(f"📦 Backing up {db_name}...")

        source_conn = sqlite3.connect(db_path)
        backup_conn = sqlite3.connect(backup_path)

        # Use SQLite's backup API
        source_conn.backup(backup_conn)

        source_conn.close()
        backup_conn.close()

        # Verify backup if requested
        if verify:
            if not verify_database(backup_path):
                print(f"❌ Backup verification failed: {backup_filename}")
                os.remove(backup_path)
                return False

        # Get file sizes
        source_size = os.path.getsize(db_path)
        backup_size = os.path.getsize(backup_path)

        print(f"✅ Backup created: {backup_filename}")
        print(f"   Source size: {source_size:,} bytes")
        print(f"   Backup size: {backup_size:,} bytes")

        return True

    except Exception as e:
        print(f"❌ Error backing up {db_name}: {e}")
        return False


def cleanup_old_backups(keep_days: int = DEFAULT_KEEP_DAYS):
    """
    Remove backups older than specified days.

    Args:
        keep_days: Number of days to keep backups
    """
    cutoff_date = datetime.now() - timedelta(days=keep_days)
    cutoff_timestamp = cutoff_date.timestamp()

    deleted_count = 0
    deleted_size = 0

    print(f"\n🧹 Cleaning up backups older than {keep_days} days...")

    for backup_file in Path(BACKUP_DIR).glob('*.db'):
        # Check file modification time
        file_mtime = backup_file.stat().st_mtime

        if file_mtime < cutoff_timestamp:
            file_size = backup_file.stat().st_size
            try:
                backup_file.unlink()
                deleted_count += 1
                deleted_size += file_size
                print(f"   Deleted: {backup_file.name} ({file_size:,} bytes)")
            except Exception as e:
                print(f"   ❌ Error deleting {backup_file.name}: {e}")

    if deleted_count > 0:
        print(f"✅ Deleted {deleted_count} old backup(s), freed {deleted_size:,} bytes")
    else:
        print(f"✅ No old backups to delete")


def get_backup_stats():
    """Print backup statistics."""
    print("\n📊 Backup Statistics:")

    if not os.path.exists(BACKUP_DIR):
        print("   No backups found")
        return

    backup_files = list(Path(BACKUP_DIR).glob('*.db'))

    if not backup_files:
        print("   No backups found")
        return

    total_size = sum(f.stat().st_size for f in backup_files)
    oldest = min(backup_files, key=lambda f: f.stat().st_mtime)
    newest = max(backup_files, key=lambda f: f.stat().st_mtime)

    print(f"   Total backups: {len(backup_files)}")
    print(f"   Total size: {total_size:,} bytes ({total_size / 1024 / 1024:.2f} MB)")
    print(f"   Oldest backup: {oldest.name}")
    print(f"   Newest backup: {newest.name}")

    # Count by database type
    by_type = {}
    for backup_file in backup_files:
        db_type = backup_file.name.split('_')[0]
        by_type[db_type] = by_type.get(db_type, 0) + 1

    print(f"   Backups by type:")
    for db_type, count in by_type.items():
        print(f"      {db_type}: {count}")


def main():
    """Main backup function."""
    parser = argparse.ArgumentParser(description='Backup ResuBoost AI databases')
    parser.add_argument(
        '--keep-days',
        type=int,
        default=DEFAULT_KEEP_DAYS,
        help=f'Number of days to keep backups (default: {DEFAULT_KEEP_DAYS})'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify database integrity before and after backup'
    )
    parser.add_argument(
        '--no-cleanup',
        action='store_true',
        help='Skip cleanup of old backups'
    )
    parser.add_argument(
        '--stats-only',
        action='store_true',
        help='Only show backup statistics, do not create backups'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("ResuBoost AI - Database Backup")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Create backup directory
    create_backup_dir()

    # Show stats only if requested
    if args.stats_only:
        get_backup_stats()
        return

    # Get list of databases
    databases = get_databases()

    if not databases:
        print("⚠️  No databases found to backup")
        return

    print(f"Found {len(databases)} database(s) to backup")
    print()

    # Backup each database
    success_count = 0
    for db_name, db_path in databases:
        if backup_database(db_name, db_path, verify=args.verify):
            success_count += 1

    print()
    print(f"✅ Successfully backed up {success_count}/{len(databases)} database(s)")

    # Cleanup old backups unless disabled
    if not args.no_cleanup:
        cleanup_old_backups(keep_days=args.keep_days)

    # Show backup statistics
    get_backup_stats()

    print()
    print("=" * 60)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Backup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Backup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
