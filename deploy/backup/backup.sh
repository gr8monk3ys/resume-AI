#!/bin/bash
#
# PostgreSQL Backup Script for ResuBoost AI
#
# This script creates compressed backups of the PostgreSQL database
# and manages backup retention.
#
# Usage:
#   ./backup.sh                    # Create backup
#   ./backup.sh --restore FILE     # Restore from backup
#   ./backup.sh --list             # List available backups
#
# Environment variables:
#   POSTGRES_HOST     - Database host (default: localhost)
#   POSTGRES_PORT     - Database port (default: 5432)
#   POSTGRES_DB       - Database name (required)
#   POSTGRES_USER     - Database user (required)
#   POSTGRES_PASSWORD - Database password (required)
#   BACKUP_DIR        - Backup directory (default: /backups)
#   RETENTION_DAYS    - Days to keep backups (default: 30)
#

set -euo pipefail

# Configuration
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-}"
POSTGRES_USER="${POSTGRES_USER:-}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    if [ -z "$POSTGRES_DB" ]; then
        log_error "POSTGRES_DB environment variable is required"
        exit 1
    fi

    if [ -z "$POSTGRES_USER" ]; then
        log_error "POSTGRES_USER environment variable is required"
        exit 1
    fi

    if [ -z "$POSTGRES_PASSWORD" ]; then
        log_error "POSTGRES_PASSWORD environment variable is required"
        exit 1
    fi

    if ! command -v pg_dump &> /dev/null; then
        log_error "pg_dump command not found. Please install PostgreSQL client tools."
        exit 1
    fi

    mkdir -p "$BACKUP_DIR"
}

create_backup() {
    check_requirements

    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="${BACKUP_DIR}/${POSTGRES_DB}_${TIMESTAMP}.sql.gz"

    log_info "Starting backup of database: $POSTGRES_DB"
    log_info "Backup file: $BACKUP_FILE"

    export PGPASSWORD="$POSTGRES_PASSWORD"

    if pg_dump \
        -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        --no-owner \
        --no-acl \
        --clean \
        --if-exists \
        | gzip > "$BACKUP_FILE"; then

        BACKUP_SIZE=$(ls -lh "$BACKUP_FILE" | awk '{print $5}')
        log_info "Backup completed successfully"
        log_info "Backup size: $BACKUP_SIZE"

        # Create latest symlink
        ln -sf "$BACKUP_FILE" "${BACKUP_DIR}/${POSTGRES_DB}_latest.sql.gz"
    else
        log_error "Backup failed!"
        rm -f "$BACKUP_FILE"
        exit 1
    fi

    unset PGPASSWORD
}

restore_backup() {
    check_requirements

    RESTORE_FILE="$1"

    if [ ! -f "$RESTORE_FILE" ]; then
        log_error "Backup file not found: $RESTORE_FILE"
        exit 1
    fi

    log_warn "This will restore the database from: $RESTORE_FILE"
    log_warn "All existing data in $POSTGRES_DB will be replaced!"
    read -p "Are you sure you want to continue? (yes/no): " CONFIRM

    if [ "$CONFIRM" != "yes" ]; then
        log_info "Restore cancelled"
        exit 0
    fi

    log_info "Starting restore..."

    export PGPASSWORD="$POSTGRES_PASSWORD"

    if gunzip -c "$RESTORE_FILE" | psql \
        -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        --quiet; then

        log_info "Restore completed successfully!"
    else
        log_error "Restore failed!"
        exit 1
    fi

    unset PGPASSWORD
}

list_backups() {
    check_requirements

    log_info "Available backups in $BACKUP_DIR:"
    echo ""

    if ls -la "${BACKUP_DIR}"/*.sql.gz 2>/dev/null; then
        echo ""
        log_info "Total backups: $(ls -1 "${BACKUP_DIR}"/*.sql.gz 2>/dev/null | wc -l)"
    else
        log_warn "No backups found"
    fi
}

cleanup_old_backups() {
    check_requirements

    log_info "Cleaning up backups older than $RETENTION_DAYS days..."

    DELETED_COUNT=$(find "$BACKUP_DIR" -name "*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete -print | wc -l)

    if [ "$DELETED_COUNT" -gt 0 ]; then
        log_info "Deleted $DELETED_COUNT old backup(s)"
    else
        log_info "No old backups to delete"
    fi
}

show_help() {
    echo "PostgreSQL Backup Script for ResuBoost AI"
    echo ""
    echo "Usage:"
    echo "  $0                    Create a new backup"
    echo "  $0 --restore FILE     Restore from a backup file"
    echo "  $0 --list             List available backups"
    echo "  $0 --cleanup          Delete backups older than RETENTION_DAYS"
    echo "  $0 --help             Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  POSTGRES_HOST     Database host (default: localhost)"
    echo "  POSTGRES_PORT     Database port (default: 5432)"
    echo "  POSTGRES_DB       Database name (required)"
    echo "  POSTGRES_USER     Database user (required)"
    echo "  POSTGRES_PASSWORD Database password (required)"
    echo "  BACKUP_DIR        Backup directory (default: /backups)"
    echo "  RETENTION_DAYS    Days to keep backups (default: 30)"
}

# Main
case "${1:-}" in
    --restore)
        if [ -z "${2:-}" ]; then
            log_error "Please specify backup file to restore"
            exit 1
        fi
        restore_backup "$2"
        ;;
    --list)
        list_backups
        ;;
    --cleanup)
        cleanup_old_backups
        ;;
    --help)
        show_help
        ;;
    *)
        create_backup
        cleanup_old_backups
        ;;
esac
