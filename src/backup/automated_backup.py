"""
Automated Backup System for MediGuard AI.
Provides automated backups of critical data with scheduling and retention.
"""

import asyncio
import logging
import os
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError

from src.settings import get_settings

logger = logging.getLogger(__name__)


class BackupType(Enum):
    """Types of backups."""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"


class BackupStatus(Enum):
    """Backup status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RESTORING = "restoring"


@dataclass
class BackupConfig:
    """Backup configuration."""
    name: str
    backup_type: BackupType
    source: str
    destination: str
    schedule: str  # Cron expression
    retention_days: int = 30
    compression: bool = True
    encryption: bool = True
    notification_emails: list[str] = None
    metadata: dict[str, Any] = None


@dataclass
class BackupJob:
    """Backup job information."""
    job_id: str
    config: BackupConfig
    status: BackupStatus
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    size_bytes: int = 0
    file_count: int = 0
    error_message: str | None = None
    backup_path: str | None = None
    checksum: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['config'] = asdict(self.config)
        data['backup_type'] = self.config.backup_type.value
        data['status'] = self.status.value
        for field in ['created_at', 'started_at', 'completed_at']:
            if data[field]:
                data[field] = getattr(self, field).isoformat()
        return data


class BackupProvider:
    """Base class for backup providers."""

    async def backup(self, source: str, destination: str, config: BackupConfig) -> dict[str, Any]:
        """Perform backup."""
        raise NotImplementedError

    async def restore(self, backup_path: str, destination: str) -> bool:
        """Restore from backup."""
        raise NotImplementedError

    async def list_backups(self, prefix: str) -> list[dict[str, Any]]:
        """List available backups."""
        raise NotImplementedError

    async def delete_backup(self, backup_path: str) -> bool:
        """Delete a backup."""
        raise NotImplementedError


class FileSystemBackupProvider(BackupProvider):
    """File system backup provider."""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def backup(self, source: str, destination: str, config: BackupConfig) -> dict[str, Any]:
        """Perform file system backup."""
        source_path = Path(source)
        dest_path = self.base_path / destination

        # Create destination directory
        dest_path.mkdir(parents=True, exist_ok=True)

        # Track statistics
        total_size = 0
        file_count = 0

        if config.backup_type == BackupType.FULL:
            # Full backup
            for item in source_path.rglob("*"):
                if item.is_file():
                    rel_path = item.relative_to(source_path)
                    dest_file = dest_path / rel_path
                    dest_file.parent.mkdir(parents=True, exist_ok=True)

                    # Copy file
                    shutil.copy2(item, dest_file)
                    total_size += item.stat().st_size
                    file_count += 1

        # Compress if enabled
        if config.compression:
            archive_path = dest_path.with_suffix('.tar.gz')
            await self._compress_directory(dest_path, archive_path)
            shutil.rmtree(dest_path)  # Remove uncompressed
            dest_path = archive_path
            total_size = dest_path.stat().st_size

        return {
            "path": str(dest_path),
            "size_bytes": total_size,
            "file_count": file_count
        }

    async def restore(self, backup_path: str, destination: str) -> bool:
        """Restore from backup."""
        try:
            backup_path = Path(backup_path)
            dest_path = Path(destination)

            # Decompress if needed
            if backup_path.suffix == '.gz':
                temp_dir = dest_path.parent / f"temp_{datetime.now().timestamp()}"
                await self._decompress_archive(backup_path, temp_dir)
                backup_path = temp_dir

            # Copy files
            if backup_path.is_dir():
                shutil.copytree(backup_path, dest_path, dirs_exist_ok=True)
            else:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_path, dest_path)

            # Cleanup temp directory
            if str(temp_dir) in str(backup_path):
                shutil.rmtree(temp_dir)

            return True
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False

    async def list_backups(self, prefix: str) -> list[dict[str, Any]]:
        """List available backups."""
        backups = []

        for item in self.base_path.glob(f"{prefix}*"):
            if item.is_file() or item.is_dir():
                stat = item.stat()
                backups.append({
                    "name": item.name,
                    "path": str(item),
                    "size_bytes": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "type": "directory" if item.is_dir() else "file"
                })

        return sorted(backups, key=lambda x: x["created_at"], reverse=True)

    async def delete_backup(self, backup_path: str) -> bool:
        """Delete a backup."""
        try:
            path = Path(backup_path)
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            return True
        except Exception as e:
            logger.error(f"Failed to delete backup: {e}")
            return False

    async def _compress_directory(self, source_dir: Path, archive_path: Path):
        """Compress directory to tar.gz."""
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(source_dir, arcname=source_dir.name)

    async def _decompress_archive(self, archive_path: Path, dest_dir: Path):
        """Decompress tar.gz archive."""
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(dest_dir)


class S3BackupProvider(BackupProvider):
    """S3 backup provider."""

    def __init__(self, bucket_name: str, aws_access_key: str, aws_secret_key: str, region: str = "us-east-1"):
        self.bucket_name = bucket_name
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=region
        )

    async def backup(self, source: str, destination: str, config: BackupConfig) -> dict[str, Any]:
        """Upload backup to S3."""
        source_path = Path(source)

        # Create temporary archive
        temp_dir = Path("/tmp/backup_temp")
        temp_dir.mkdir(exist_ok=True)
        archive_path = temp_dir / f"{destination}.tar.gz"

        # Create archive
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(source_path, arcname=source_path.name)

        try:
            # Upload to S3
            file_size = archive_path.stat().st_size
            file_count = len(list(source_path.rglob("*"))) if source_path.is_dir() else 1

            self.s3_client.upload_file(
                str(archive_path),
                self.bucket_name,
                destination,
                ExtraArgs={
                    'ServerSideEncryption': 'AES256' if config.encryption else None
                }
            )

            return {
                "path": f"s3://{self.bucket_name}/{destination}",
                "size_bytes": file_size,
                "file_count": file_count
            }
        finally:
            # Cleanup
            archive_path.unlink()

    async def restore(self, backup_path: str, destination: str) -> bool:
        """Restore from S3 backup."""
        try:
            # Parse S3 path
            if backup_path.startswith("s3://"):
                backup_path = backup_path[5:]  # Remove s3://
                bucket, key = backup_path.split("/", 1)
            else:
                key = backup_path
                bucket = self.bucket_name

            # Download to temp location
            temp_dir = Path("/tmp/backup_restore")
            temp_dir.mkdir(exist_ok=True)
            temp_file = temp_dir / Path(key).name

            self.s3_client.download_file(bucket, key, str(temp_file))

            # Extract
            dest_path = Path(destination)
            with tarfile.open(temp_file, "r:gz") as tar:
                tar.extractall(dest_path)

            # Cleanup
            temp_file.unlink()

            return True
        except Exception as e:
            logger.error(f"S3 restore failed: {e}")
            return False

    async def list_backups(self, prefix: str) -> list[dict[str, Any]]:
        """List backups in S3."""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )

            backups = []
            for obj in response.get('Contents', []):
                backups.append({
                    "name": obj['Key'],
                    "path": f"s3://{self.bucket_name}/{obj['Key']}",
                    "size_bytes": obj['Size'],
                    "created_at": obj['LastModified'].isoformat(),
                    "type": "file"
                })

            return sorted(backups, key=lambda x: x["created_at"], reverse=True)
        except ClientError as e:
            logger.error(f"Failed to list S3 backups: {e}")
            return []

    async def delete_backup(self, backup_path: str) -> bool:
        """Delete backup from S3."""
        try:
            if backup_path.startswith("s3://"):
                backup_path = backup_path[5:]
                bucket, key = backup_path.split("/", 1)
            else:
                key = backup_path
                bucket = self.bucket_name

            self.s3_client.delete_object(Bucket=bucket, Key=key)
            return True
        except ClientError as e:
            logger.error(f"Failed to delete S3 backup: {e}")
            return False


class DatabaseBackupProvider(BackupProvider):
    """Database backup provider."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string

    async def backup(self, source: str, destination: str, config: BackupConfig) -> dict[str, Any]:
        """Backup database."""
        # This would implement database-specific backup logic
        # For example, PostgreSQL pg_dump or MongoDB mongodump
        pass

    async def restore(self, backup_path: str, destination: str) -> bool:
        """Restore database."""
        pass


class BackupManager:
    """Manages backup operations."""

    def __init__(self):
        self.providers: dict[str, BackupProvider] = {}
        self.configs: dict[str, BackupConfig] = {}
        self.jobs: dict[str, BackupJob] = {}
        self.scheduler_running = False

    def register_provider(self, name: str, provider: BackupProvider):
        """Register a backup provider."""
        self.providers[name] = provider

    def add_config(self, config: BackupConfig):
        """Add a backup configuration."""
        self.configs[config.name] = config

    async def create_backup_job(self, config_name: str) -> str:
        """Create and start a backup job."""
        if config_name not in self.configs:
            raise ValueError(f"Backup config '{config_name}' not found")

        config = self.configs[config_name]
        job_id = f"backup_{config_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        job = BackupJob(
            job_id=job_id,
            config=config,
            status=BackupStatus.PENDING,
            created_at=datetime.utcnow()
        )

        self.jobs[job_id] = job

        # Start backup in background
        asyncio.create_task(self._execute_backup(job_id))

        return job_id

    async def _execute_backup(self, job_id: str):
        """Execute a backup job."""
        job = self.jobs[job_id]
        job.status = BackupStatus.RUNNING
        job.started_at = datetime.utcnow()

        try:
            config = job.config
            provider = self.providers.get(config.destination.split(":")[0])

            if not provider:
                raise ValueError(f"No provider for destination: {config.destination}")

            # Perform backup
            result = await provider.backup(config.source, f"{config.name}/{job_id}", config)

            # Update job
            job.status = BackupStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.size_bytes = result["size_bytes"]
            job.file_count = result["file_count"]
            job.backup_path = result["path"]

            # Calculate checksum
            job.checksum = await self._calculate_checksum(result["path"])

            logger.info(f"Backup {job_id} completed successfully")

            # Send notification
            await self._send_notification(job, "completed")

        except Exception as e:
            job.status = BackupStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.error_message = str(e)

            logger.error(f"Backup {job_id} failed: {e}")

            # Send notification
            await self._send_notification(job, "failed")

    async def restore_backup(self, backup_path: str, destination: str) -> bool:
        """Restore from backup."""
        # Determine provider from backup path
        if backup_path.startswith("s3://"):
            provider = self.providers.get("s3")
        else:
            provider = self.providers.get("filesystem")

        if not provider:
            raise ValueError("No suitable provider found for backup")

        return await provider.restore(backup_path, destination)

    async def list_backups(self, config_name: str = None) -> list[dict[str, Any]]:
        """List available backups."""
        all_backups = []

        if config_name:
            configs = [self.configs.get(config_name)]
        else:
            configs = self.configs.values()

        for config in configs:
            if not config:
                continue

            provider = self.providers.get(config.destination.split(":")[0])
            if provider:
                backups = await provider.list_backups(f"{config.name}/")
                all_backups.extend(backups)

        return sorted(all_backups, key=lambda x: x["created_at"], reverse=True)

    async def delete_backup(self, backup_path: str) -> bool:
        """Delete a backup."""
        if backup_path.startswith("s3://"):
            provider = self.providers.get("s3")
        else:
            provider = self.providers.get("filesystem")

        if provider:
            return await provider.delete_backup(backup_path)

        return False

    async def cleanup_old_backups(self):
        """Clean up backups older than retention period."""
        for config in self.configs.values():
            cutoff_date = datetime.utcnow() - timedelta(days=config.retention_days)

            provider = self.providers.get(config.destination.split(":")[0])
            if not provider:
                continue

            backups = await provider.list_backups(f"{config.name}/")

            for backup in backups:
                backup_date = datetime.fromisoformat(backup["created_at"])
                if backup_date < cutoff_date:
                    await provider.delete_backup(backup["path"])
                    logger.info(f"Deleted old backup: {backup['path']}")

    async def get_job_status(self, job_id: str) -> dict[str, Any] | None:
        """Get backup job status."""
        job = self.jobs.get(job_id)
        return job.to_dict() if job else None

    async def list_jobs(self) -> list[dict[str, Any]]:
        """List all backup jobs."""
        return [job.to_dict() for job in self.jobs.values()]

    async def _calculate_checksum(self, path: str) -> str:
        """Calculate checksum for backup integrity."""
        # Simple checksum calculation
        import hashlib

        if os.path.isfile(path):
            with open(path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        else:
            # For directories, calculate based on file list and sizes
            checksum = hashlib.sha256()
            for root, dirs, files in os.walk(path):
                for file in sorted(files):
                    file_path = os.path.join(root, file)
                    checksum.update(file.encode())
                    checksum.update(str(os.path.getsize(file_path)).encode())
            return checksum.hexdigest()

    async def _send_notification(self, job: BackupJob, status: str):
        """Send backup notification."""
        # Implement email/webhook notifications
        if job.config.notification_emails:
            message = f"""
            Backup {status}: {job.job_id}
            Config: {job.config.name}
            Started: {job.started_at}
            Completed: {job.completed_at}
            Size: {job.size_bytes} bytes
            Files: {job.file_count}
            """

            if job.error_message:
                message += f"\nError: {job.error_message}"

            logger.info(f"Backup notification: {message}")
            # Here you would implement actual email sending


# Global backup manager
_backup_manager: BackupManager | None = None


async def get_backup_manager() -> BackupManager:
    """Get or create the global backup manager."""
    global _backup_manager

    if not _backup_manager:
        _backup_manager = BackupManager()

        # Register providers based on configuration
        settings = get_settings()

        # File system provider
        fs_provider = FileSystemBackupProvider("/tmp/backups")
        _backup_manager.register_provider("filesystem", fs_provider)

        # S3 provider if configured
        if hasattr(settings, 'AWS_ACCESS_KEY_ID'):
            s3_provider = S3BackupProvider(
                bucket_name=settings.AWS_S3_BUCKET,
                aws_access_key=settings.AWS_ACCESS_KEY_ID,
                aws_secret_key=settings.AWS_SECRET_ACCESS_KEY,
                region=settings.AWS_REGION
            )
            _backup_manager.register_provider("s3", s3_provider)

        # Add default backup configs
        await _setup_default_configs()

        # Start cleanup scheduler
        asyncio.create_task(_cleanup_scheduler())

    return _backup_manager


async def _setup_default_configs():
    """Setup default backup configurations."""
    manager = await get_backup_manager()

    # OpenSearch backup
    opensearch_config = BackupConfig(
        name="opensearch",
        backup_type=BackupType.FULL,
        source="/var/lib/opensearch",
        destination="filesystem:backups/opensearch",
        schedule="0 2 * * *",  # Daily at 2 AM
        retention_days=30,
        compression=True,
        encryption=True
    )
    manager.add_config(opensearch_config)

    # Redis backup
    redis_config = BackupConfig(
        name="redis",
        backup_type=BackupType.FULL,
        source="/var/lib/redis",
        destination="filesystem:backups/redis",
        schedule="0 3 * * *",  # Daily at 3 AM
        retention_days=7,
        compression=True,
        encryption=True
    )
    manager.add_config(redis_config)

    # Application data backup
    app_config = BackupConfig(
        name="application",
        backup_type=BackupType.INCREMENTAL,
        source="/app/data",
        destination="filesystem:backups/application",
        schedule="0 4 * * *",  # Daily at 4 AM
        retention_days=90,
        compression=True,
        encryption=True
    )
    manager.add_config(app_config)


async def _cleanup_scheduler():
    """Schedule periodic cleanup of old backups."""
    while True:
        try:
            manager = await get_backup_manager()
            await manager.cleanup_old_backups()

            # Run daily
            await asyncio.sleep(86400)
        except Exception as e:
            logger.error(f"Backup cleanup error: {e}")
            await asyncio.sleep(3600)  # Retry in 1 hour


# CLI commands for backup management
async def create_backup(config_name: str):
    """Create a backup for the specified configuration."""
    manager = await get_backup_manager()
    job_id = await manager.create_backup_job(config_name)
    print(f"Backup job created: {job_id}")

    # Wait for completion
    while True:
        job = await manager.get_job_status(job_id)
        if job['status'] in ['completed', 'failed']:
            break
        await asyncio.sleep(5)

    print(f"Backup {job['status']}: {job_id}")
    if job['error_message']:
        print(f"Error: {job['error_message']}")


async def list_backups(config_name: str = None):
    """List available backups."""
    manager = await get_backup_manager()
    backups = await manager.list_backups(config_name)

    for backup in backups:
        print(f"{backup['created_at']}: {backup['name']} ({backup['size_bytes']} bytes)")


async def restore_backup(backup_path: str, destination: str):
    """Restore from backup."""
    manager = await get_backup_manager()
    success = await manager.restore_backup(backup_path, destination)

    if success:
        print(f"Successfully restored from {backup_path}")
    else:
        print(f"Failed to restore from {backup_path}")
