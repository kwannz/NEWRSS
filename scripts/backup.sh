#!/bin/bash

# NEWRSS Production Backup Script
# Comprehensive backup system with retention policy and disaster recovery capability

set -euo pipefail

# Configuration
BACKUP_DIR="/var/backups/newrss"
S3_BUCKET="${BACKUP_S3_BUCKET:-}"
RETENTION_DAYS="${DB_BACKUP_RETENTION_DAYS:-30}"
LOG_FILE="/var/log/newrss/backup.log"

# Database configuration
DB_HOST="${POSTGRES_HOST:-postgres}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-newrss_prod}"
DB_USER="${POSTGRES_USER:-newrss_prod}"
DB_PASSWORD="${POSTGRES_PASSWORD:-}"

# Timestamps
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE_DIR=$(date +%Y-%m-%d)

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Check dependencies
check_dependencies() {
    log "Checking backup dependencies..."
    
    if ! command -v pg_dump &> /dev/null; then
        error_exit "pg_dump not found. Please install PostgreSQL client tools."
    fi
    
    if ! command -v gzip &> /dev/null; then
        error_exit "gzip not found."
    fi
    
    if [[ -n "$S3_BUCKET" ]] && ! command -v aws &> /dev/null; then
        error_exit "aws CLI not found. Please install AWS CLI for S3 backup."
    fi
    
    log "All dependencies satisfied."
}

# Create backup directories
setup_directories() {
    log "Setting up backup directories..."
    
    mkdir -p "$BACKUP_DIR"/{database,logs,config,application}/"$DATE_DIR"
    chmod 750 "$BACKUP_DIR"
    
    log "Backup directories created: $BACKUP_DIR"
}

# Database backup
backup_database() {
    log "Starting database backup..."
    
    local backup_file="$BACKUP_DIR/database/$DATE_DIR/database_backup_$TIMESTAMP.sql"
    
    # Set PostgreSQL password
    export PGPASSWORD="$DB_PASSWORD"
    
    # Create database backup
    pg_dump \
        --host="$DB_HOST" \
        --port="$DB_PORT" \
        --username="$DB_USER" \
        --dbname="$DB_NAME" \
        --format=custom \
        --compress=9 \
        --verbose \
        --file="$backup_file" \
        --no-password
    
    if [[ $? -eq 0 ]]; then
        # Compress backup
        gzip "$backup_file"
        backup_file="$backup_file.gz"
        
        # Verify backup integrity
        gunzip -t "$backup_file"
        
        if [[ $? -eq 0 ]]; then
            local size=$(du -h "$backup_file" | cut -f1)
            log "Database backup completed successfully: $backup_file ($size)"
            echo "$backup_file"
        else
            error_exit "Database backup verification failed"
        fi
    else
        error_exit "Database backup failed"
    fi
    
    unset PGPASSWORD
}

# Configuration backup
backup_configuration() {
    log "Starting configuration backup..."
    
    local config_backup="$BACKUP_DIR/config/$DATE_DIR/config_backup_$TIMESTAMP.tar.gz"
    
    # Files and directories to backup
    local config_items=(
        "/app/.env.production"
        "/etc/nginx/nginx.conf"
        "/app/nginx/nginx.prod.conf"
        "/app/docker-compose.prod.yml"
        "/app/scripts/"
        "/etc/ssl/certs/"
    )
    
    # Create configuration archive
    tar -czf "$config_backup" \
        --ignore-failed-read \
        "${config_items[@]}" \
        2>/dev/null || true
    
    if [[ -f "$config_backup" ]]; then
        local size=$(du -h "$config_backup" | cut -f1)
        log "Configuration backup completed: $config_backup ($size)"
        echo "$config_backup"
    else
        log "WARNING: Configuration backup may be incomplete"
        echo ""
    fi
}

# Application logs backup
backup_logs() {
    log "Starting logs backup..."
    
    local logs_backup="$BACKUP_DIR/logs/$DATE_DIR/logs_backup_$TIMESTAMP.tar.gz"
    local log_dirs=(
        "/var/log/newrss/"
        "/var/log/nginx/"
    )
    
    # Create logs archive
    tar -czf "$logs_backup" \
        --ignore-failed-read \
        "${log_dirs[@]}" \
        2>/dev/null || true
    
    if [[ -f "$logs_backup" ]]; then
        local size=$(du -h "$logs_backup" | cut -f1)
        log "Logs backup completed: $logs_backup ($size)"
        echo "$logs_backup"
    else
        log "WARNING: Logs backup may be incomplete"
        echo ""
    fi
}

# Application data backup
backup_application_data() {
    log "Starting application data backup..."
    
    local app_backup="$BACKUP_DIR/application/$DATE_DIR/app_data_backup_$TIMESTAMP.tar.gz"
    
    # Application data directories
    local app_dirs=(
        "/app/data/"
        "/app/uploads/"
        "/tmp/celerybeat-schedule"
    )
    
    # Create application data archive
    tar -czf "$app_backup" \
        --ignore-failed-read \
        "${app_dirs[@]}" \
        2>/dev/null || true
    
    if [[ -f "$app_backup" ]]; then
        local size=$(du -h "$app_backup" | cut -f1)
        log "Application data backup completed: $app_backup ($size)"
        echo "$app_backup"
    else
        log "WARNING: Application data backup may be incomplete"
        echo ""
    fi
}

# Upload to S3 (if configured)
upload_to_s3() {
    local file_path="$1"
    
    if [[ -z "$S3_BUCKET" ]] || [[ -z "$file_path" ]] || [[ ! -f "$file_path" ]]; then
        return 0
    fi
    
    log "Uploading to S3: $file_path"
    
    local s3_key="newrss-backups/$DATE_DIR/$(basename "$file_path")"
    
    aws s3 cp "$file_path" "s3://$S3_BUCKET/$s3_key" \
        --storage-class STANDARD_IA \
        --server-side-encryption AES256
    
    if [[ $? -eq 0 ]]; then
        log "Successfully uploaded to S3: s3://$S3_BUCKET/$s3_key"
    else
        log "WARNING: Failed to upload to S3: $file_path"
    fi
}

# Cleanup old backups
cleanup_old_backups() {
    log "Cleaning up old backups (older than $RETENTION_DAYS days)..."
    
    local deleted_count=0
    
    # Find and delete old local backups
    while IFS= read -r -d '' old_dir; do
        if [[ -d "$old_dir" ]]; then
            rm -rf "$old_dir"
            deleted_count=$((deleted_count + 1))
            log "Removed old backup directory: $old_dir"
        fi
    done < <(find "$BACKUP_DIR" -type d -name "20*-*-*" -mtime +$RETENTION_DAYS -print0 2>/dev/null || true)
    
    # Cleanup old S3 backups (if configured)
    if [[ -n "$S3_BUCKET" ]]; then
        local cutoff_date=$(date -d "$RETENTION_DAYS days ago" +%Y-%m-%d)
        
        aws s3 ls "s3://$S3_BUCKET/newrss-backups/" --recursive | \
        awk '{print $4}' | \
        while read -r s3_key; do
            local file_date=$(echo "$s3_key" | grep -o '20[0-9][0-9]-[0-9][0-9]-[0-9][0-9]' | head -1)
            if [[ -n "$file_date" ]] && [[ "$file_date" < "$cutoff_date" ]]; then
                aws s3 rm "s3://$S3_BUCKET/$s3_key"
                log "Removed old S3 backup: s3://$S3_BUCKET/$s3_key"
                deleted_count=$((deleted_count + 1))
            fi
        done
    fi
    
    log "Cleanup completed: $deleted_count old backups removed"
}

# Generate backup report
generate_backup_report() {
    local db_backup="$1"
    local config_backup="$2"
    local logs_backup="$3"
    local app_backup="$4"
    
    local report_file="$BACKUP_DIR/backup_report_$TIMESTAMP.json"
    
    cat > "$report_file" << EOF
{
    "backup_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "timestamp": "$TIMESTAMP",
    "status": "completed",
    "files": {
        "database": {
            "file": "$(basename "$db_backup")",
            "size": "$(du -h "$db_backup" 2>/dev/null | cut -f1 || echo "N/A")",
            "path": "$db_backup"
        },
        "configuration": {
            "file": "$(basename "$config_backup" 2>/dev/null || echo "N/A")",
            "size": "$(du -h "$config_backup" 2>/dev/null | cut -f1 || echo "N/A")",
            "path": "$config_backup"
        },
        "logs": {
            "file": "$(basename "$logs_backup" 2>/dev/null || echo "N/A")",
            "size": "$(du -h "$logs_backup" 2>/dev/null | cut -f1 || echo "N/A")",
            "path": "$logs_backup"
        },
        "application_data": {
            "file": "$(basename "$app_backup" 2>/dev/null || echo "N/A")",
            "size": "$(du -h "$app_backup" 2>/dev/null | cut -f1 || echo "N/A")",
            "path": "$app_backup"
        }
    },
    "retention_days": $RETENTION_DAYS,
    "s3_bucket": "$S3_BUCKET"
}
EOF
    
    log "Backup report generated: $report_file"
    
    # Upload report to S3
    upload_to_s3 "$report_file"
}

# Main backup process
main() {
    log "=== Starting NEWRSS backup process ==="
    
    # Pre-flight checks
    check_dependencies
    setup_directories
    
    # Perform backups
    local db_backup
    local config_backup
    local logs_backup
    local app_backup
    
    db_backup=$(backup_database)
    config_backup=$(backup_configuration)
    logs_backup=$(backup_logs)
    app_backup=$(backup_application_data)
    
    # Upload to S3 (if configured)
    if [[ -n "$S3_BUCKET" ]]; then
        log "Uploading backups to S3..."
        upload_to_s3 "$db_backup"
        upload_to_s3 "$config_backup"
        upload_to_s3 "$logs_backup"
        upload_to_s3 "$app_backup"
    fi
    
    # Cleanup old backups
    cleanup_old_backups
    
    # Generate report
    generate_backup_report "$db_backup" "$config_backup" "$logs_backup" "$app_backup"
    
    # Calculate total backup size
    local total_size=$(du -sh "$BACKUP_DIR/$DATE_DIR" 2>/dev/null | cut -f1 || echo "N/A")
    
    log "=== Backup process completed successfully ==="
    log "Total backup size: $total_size"
    log "Backup location: $BACKUP_DIR/$DATE_DIR"
    
    if [[ -n "$S3_BUCKET" ]]; then
        log "S3 backup location: s3://$S3_BUCKET/newrss-backups/$DATE_DIR"
    fi
}

# Handle signals
trap 'error_exit "Backup interrupted"' INT TERM

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"
touch "$LOG_FILE"

# Run main backup process
main "$@"