#!/bin/bash

# Database Backup Script for ManageIt Production
# Run this script regularly to backup your database

set -e

# Load environment variables
source .env.production

# Configuration
BACKUP_DIR="/var/backups/manageit"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="manageit_backup_${DATE}.sql"
RETENTION_DAYS=30

# Create backup directory
mkdir -p $BACKUP_DIR

echo "🗄️ Starting database backup..."

# Create database backup
mysqldump -h $DB_HOST -u $DB_USER -p$DB_PASSWORD \
    --single-transaction \
    --routines \
    --triggers \
    --events \
    --hex-blob \
    $DB_NAME > $BACKUP_DIR/$BACKUP_FILE

# Compress backup
gzip $BACKUP_DIR/$BACKUP_FILE

echo "✅ Database backup created: $BACKUP_DIR/${BACKUP_FILE}.gz"

# Remove old backups
find $BACKUP_DIR -name "manageit_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "🧹 Old backups cleaned up (older than $RETENTION_DAYS days)"

# Backup application files
tar -czf $BACKUP_DIR/app_files_${DATE}.tar.gz \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='logs' \
    .

echo "✅ Application files backup created: $BACKUP_DIR/app_files_${DATE}.tar.gz"

# Remove old app backups
find $BACKUP_DIR -name "app_files_*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "🎉 Backup process completed successfully!"
echo "📊 Backup summary:"
ls -lh $BACKUP_DIR/*${DATE}*
