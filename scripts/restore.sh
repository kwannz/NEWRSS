#!/bin/bash

# NEWRSS Production Restore Script
# Disaster recovery and point-in-time restoration capability

set -euo pipefail

# Configuration
BACKUP_DIR="/var/backups/newrss"
S3_BUCKET="${BACKUP_S3_BUCKET:-}"
LOG_FILE="/var/log/newrss/restore.log"

# Database configuration
DB_HOST="${POSTGRES_HOST:-postgres}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-newrss_prod}"
DB_USER="${POSTGRES_USER:-newrss_prod}"
DB_PASSWORD="${POSTGRES_PASSWORD:-}"

# Restore configuration
RESTORE_DATE=""
RESTORE_TYPE="full"  # full, database, config, logs, app-data
DRY_RUN=false
FORCE_RESTORE=false

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Show usage
usage() {
    cat << EOF
NEWRSS Restore Script

Usage: $0 [OPTIONS]

OPTIONS:
    -d, --date DATE         Restore date (YYYY-MM-DD format)
    -t, --type TYPE         Restore type: full, database, config, logs, app-data
    -n, --dry-run          Perform dry run without actual restore
    -f, --force            Force restore without confirmation prompts
    -s, --from-s3          Restore from S3 backup
    -h, --help             Show this help message

EXAMPLES:
    # Full restore from latest backup
    $0 --date 2024-01-15 --type full

    # Database-only restore with dry run
    $0 --date 2024-01-15 --type database --dry-run

    # Force restore from S3
    $0 --date 2024-01-15 --from-s3 --force

EOF
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--date)
                RESTORE_DATE="$2"
                shift 2
                ;;
            -t|--type)
                RESTORE_TYPE="$2"
                shift 2
                ;;
            -n|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -f|--force)
                FORCE_RESTORE=true
                shift
                ;;
            -s|--from-s3)
                FROM_S3=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                error_exit "Unknown option: $1. Use --help for usage information."
                ;;
        esac
    done
    
    # Validate required arguments
    if [[ -z "$RESTORE_DATE" ]]; then
        error_exit "Restore date is required. Use --date YYYY-MM-DD"
    fi
    
    # Validate date format
    if ! date -d "$RESTORE_DATE" >/dev/null 2>&1; then
        error_exit "Invalid date format: $RESTORE_DATE. Use YYYY-MM-DD format."
    fi
    
    # Validate restore type
    case "$RESTORE_TYPE" in
        full|database|config|logs|app-data)
            ;;
        *)
            error_exit "Invalid restore type: $RESTORE_TYPE. Valid types: full, database, config, logs, app-data"
            ;;
    esac
}

# Check dependencies
check_dependencies() {
    log "Checking restore dependencies..."
    
    if ! command -v pg_restore &> /dev/null; then
        error_exit "pg_restore not found. Please install PostgreSQL client tools."
    fi
    
    if ! command -v tar &> /dev/null; then
        error_exit "tar not found."
    fi
    
    if ! command -v gzip &> /dev/null; then
        error_exit "gzip not found."
    fi
    
    if [[ "${FROM_S3:-false}" == "true" ]] && ! command -v aws &> /dev/null; then
        error_exit "aws CLI not found. Please install AWS CLI for S3 restore."
    fi
    
    log "All dependencies satisfied."
}

# Find available backups
find_available_backups() {
    log "Searching for available backups for date: $RESTORE_DATE"
    
    local backup_path="$BACKUP_DIR/$RESTORE_DATE"
    local backups_found=()
    
    # Check local backups
    if [[ -d "$backup_path" ]]; then
        log "Found local backup directory: $backup_path"
        
        # Find specific backup files
        if [[ -n "$(find "$backup_path" -name "database_backup_*.sql.gz" 2>/dev/null)" ]]; then
            backups_found+=("database")
        fi
        
        if [[ -n "$(find "$backup_path" -name "config_backup_*.tar.gz" 2>/dev/null)" ]]; then
            backups_found+=("config")
        fi
        
        if [[ -n "$(find "$backup_path" -name "logs_backup_*.tar.gz" 2>/dev/null)" ]]; then
            backups_found+=("logs")
        fi
        
        if [[ -n "$(find "$backup_path" -name "app_data_backup_*.tar.gz" 2>/dev/null)" ]]; then
            backups_found+=("app-data")
        fi
    fi
    
    # Check S3 backups (if configured and requested)
    if [[ "${FROM_S3:-false}" == "true" ]] && [[ -n "$S3_BUCKET" ]]; then
        log "Checking S3 for backups..."
        
        local s3_prefix="newrss-backups/$RESTORE_DATE"
        local s3_files
        s3_files=$(aws s3 ls "s3://$S3_BUCKET/$s3_prefix/" 2>/dev/null || echo "")
        
        if [[ -n "$s3_files" ]]; then
            log "Found S3 backups for $RESTORE_DATE"
            # Download S3 backups
            download_s3_backups "$s3_prefix"
        fi
    fi
    
    if [[ ${#backups_found[@]} -eq 0 ]]; then
        error_exit "No backups found for date: $RESTORE_DATE"
    fi
    
    log "Available backup types: ${backups_found[*]}"
}

# Download backups from S3
download_s3_backups() {
    local s3_prefix="$1"
    local download_path="$BACKUP_DIR/$RESTORE_DATE"
    
    log "Downloading backups from S3..."
    mkdir -p "$download_path"
    
    # Download all backup files for the date
    aws s3 sync "s3://$S3_BUCKET/$s3_prefix/" "$download_path/" \
        --exclude "*" \
        --include "*.sql.gz" \
        --include "*.tar.gz"
    
    if [[ $? -eq 0 ]]; then
        log "S3 backups downloaded successfully"
    else
        error_exit "Failed to download backups from S3"
    fi
}

# Confirm restore operation
confirm_restore() {
    if [[ "$FORCE_RESTORE" == "true" ]] || [[ "$DRY_RUN" == "true" ]]; then
        return 0
    fi
    
    echo
    echo "=========================================="
    echo "DISASTER RECOVERY RESTORE CONFIRMATION"
    echo "=========================================="
    echo "Restore Date: $RESTORE_DATE"
    echo "Restore Type: $RESTORE_TYPE"
    echo "Target Database: $DB_NAME"
    echo "=========================================="
    echo
    echo "WARNING: This operation will:"
    
    case "$RESTORE_TYPE" in
        full)
            echo "  - REPLACE the entire database with backup data"
            echo "  - OVERWRITE current configuration files"
            echo "  - REPLACE application data"
            echo "  - OVERWRITE current logs"
            ;;
        database)
            echo "  - REPLACE the entire database with backup data"
            echo "  - ALL CURRENT DATA WILL BE LOST"
            ;;
        config)
            echo "  - OVERWRITE current configuration files"
            ;;
        logs)
            echo "  - OVERWRITE current log files"
            ;;
        app-data)
            echo "  - REPLACE current application data"
            ;;
    esac
    
    echo
    echo "This action is IRREVERSIBLE!"
    echo
    read -p "Are you sure you want to proceed? (type 'YES' to confirm): " confirmation
    
    if [[ "$confirmation" != "YES" ]]; then
        log "Restore cancelled by user"
        exit 0
    fi
}

# Create pre-restore backup
create_pre_restore_backup() {
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would create pre-restore backup"
        return 0
    fi
    
    log "Creating pre-restore backup of current state..."
    
    local pre_restore_dir="$BACKUP_DIR/pre-restore-$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$pre_restore_dir"
    
    # Quick database backup
    export PGPASSWORD="$DB_PASSWORD"
    pg_dump \
        --host="$DB_HOST" \
        --port="$DB_PORT" \
        --username="$DB_USER" \
        --dbname="$DB_NAME" \
        --format=custom \
        --file="$pre_restore_dir/pre_restore_database.sql"
    
    unset PGPASSWORD
    
    log "Pre-restore backup created: $pre_restore_dir"
}

# Restore database
restore_database() {
    log "Starting database restore..."
    
    local backup_path="$BACKUP_DIR/$RESTORE_DATE"
    local db_backup_file
    db_backup_file=$(find "$backup_path" -name "database_backup_*.sql.gz" | head -1)
    
    if [[ -z "$db_backup_file" ]]; then
        error_exit "Database backup file not found for date: $RESTORE_DATE"
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would restore database from: $db_backup_file"
        return 0
    fi
    
    log "Restoring database from: $db_backup_file"
    
    # Decompress backup file
    local temp_sql_file="/tmp/restore_$(date +%s).sql"
    gunzip -c "$db_backup_file" > "$temp_sql_file"
    
    # Stop application services to prevent connections
    log "Stopping application services..."
    docker-compose -f /app/docker-compose.prod.yml stop backend celery-worker celery-beat || true
    
    # Terminate existing connections
    export PGPASSWORD="$DB_PASSWORD"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "
        SELECT pg_terminate_backend(pid) 
        FROM pg_stat_activity 
        WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();
    " || true
    
    # Drop and recreate database
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME;"
    
    # Restore database
    pg_restore \
        --host="$DB_HOST" \
        --port="$DB_PORT" \
        --username="$DB_USER" \
        --dbname="$DB_NAME" \
        --verbose \
        --clean \
        --no-owner \
        --no-privileges \
        "$temp_sql_file"
    
    if [[ $? -eq 0 ]]; then
        log "Database restore completed successfully"
    else
        error_exit "Database restore failed"
    fi
    
    # Cleanup temp file
    rm -f "$temp_sql_file"
    unset PGPASSWORD
    
    # Restart application services
    log "Restarting application services..."
    docker-compose -f /app/docker-compose.prod.yml up -d backend celery-worker celery-beat
}

# Restore configuration
restore_configuration() {
    log "Starting configuration restore..."
    
    local backup_path="$BACKUP_DIR/$RESTORE_DATE"
    local config_backup_file
    config_backup_file=$(find "$backup_path" -name "config_backup_*.tar.gz" | head -1)
    
    if [[ -z "$config_backup_file" ]]; then
        error_exit "Configuration backup file not found for date: $RESTORE_DATE"
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would restore configuration from: $config_backup_file"
        return 0
    fi
    
    log "Restoring configuration from: $config_backup_file"
    
    # Extract configuration files
    tar -xzf "$config_backup_file" -C / --overwrite
    
    if [[ $? -eq 0 ]]; then
        log "Configuration restore completed successfully"
        
        # Restart nginx if configuration was restored
        log "Restarting nginx..."
        docker-compose -f /app/docker-compose.prod.yml restart nginx || true
    else
        error_exit "Configuration restore failed"
    fi
}

# Restore logs
restore_logs() {
    log "Starting logs restore..."
    
    local backup_path="$BACKUP_DIR/$RESTORE_DATE"
    local logs_backup_file
    logs_backup_file=$(find "$backup_path" -name "logs_backup_*.tar.gz" | head -1)
    
    if [[ -z "$logs_backup_file" ]]; then
        error_exit "Logs backup file not found for date: $RESTORE_DATE"
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would restore logs from: $logs_backup_file"
        return 0
    fi
    
    log "Restoring logs from: $logs_backup_file"
    
    # Extract log files
    tar -xzf "$logs_backup_file" -C / --overwrite
    
    if [[ $? -eq 0 ]]; then
        log "Logs restore completed successfully"
    else
        error_exit "Logs restore failed"
    fi
}

# Restore application data
restore_app_data() {
    log "Starting application data restore..."
    
    local backup_path="$BACKUP_DIR/$RESTORE_DATE"
    local app_backup_file
    app_backup_file=$(find "$backup_path" -name "app_data_backup_*.tar.gz" | head -1)
    
    if [[ -z "$app_backup_file" ]]; then
        error_exit "Application data backup file not found for date: $RESTORE_DATE"
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would restore application data from: $app_backup_file"
        return 0
    fi
    
    log "Restoring application data from: $app_backup_file"
    
    # Extract application data
    tar -xzf "$app_backup_file" -C / --overwrite
    
    if [[ $? -eq 0 ]]; then
        log "Application data restore completed successfully"
    else
        error_exit "Application data restore failed"
    fi
}

# Post-restore verification
verify_restore() {
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would verify restore"
        return 0
    fi
    
    log "Verifying restore..."
    
    # Wait for services to start
    sleep 30
    
    # Check database connectivity
    export PGPASSWORD="$DB_PASSWORD"
    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT COUNT(*) FROM news_items;" >/dev/null 2>&1; then
        log "Database verification: PASSED"
    else
        log "Database verification: FAILED"
    fi
    unset PGPASSWORD
    
    # Check application health
    if curl -f http://localhost:8000/health >/dev/null 2>&1; then
        log "Application health check: PASSED"
    else
        log "Application health check: FAILED"
    fi
    
    log "Restore verification completed"
}

# Generate restore report
generate_restore_report() {
    local report_file="$BACKUP_DIR/restore_report_$(date +%Y%m%d_%H%M%S).json"
    
    cat > "$report_file" << EOF
{
    "restore_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "backup_date": "$RESTORE_DATE",
    "restore_type": "$RESTORE_TYPE",
    "dry_run": $DRY_RUN,
    "status": "completed",
    "database": "$DB_NAME",
    "restored_from": "${FROM_S3:-false}",
    "s3_bucket": "$S3_BUCKET"
}
EOF
    
    log "Restore report generated: $report_file"
}

# Main restore process
main() {
    log "=== Starting NEWRSS restore process ==="
    log "Restore date: $RESTORE_DATE"
    log "Restore type: $RESTORE_TYPE"
    log "Dry run: $DRY_RUN"
    
    # Pre-flight checks
    check_dependencies
    find_available_backups
    
    # Confirmation
    confirm_restore
    
    # Create pre-restore backup
    create_pre_restore_backup
    
    # Perform restore based on type
    case "$RESTORE_TYPE" in
        full)
            restore_database
            restore_configuration
            restore_logs
            restore_app_data
            ;;
        database)
            restore_database
            ;;
        config)
            restore_configuration
            ;;
        logs)
            restore_logs
            ;;
        app-data)
            restore_app_data
            ;;
    esac
    
    # Post-restore verification
    verify_restore
    
    # Generate report
    generate_restore_report
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "=== DRY RUN restore process completed ==="
    else
        log "=== Restore process completed successfully ==="
        log "Please verify application functionality and monitor for issues"
    fi
}

# Handle signals
trap 'error_exit "Restore interrupted"' INT TERM

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"
touch "$LOG_FILE"

# Parse arguments and run
parse_arguments "$@"
main