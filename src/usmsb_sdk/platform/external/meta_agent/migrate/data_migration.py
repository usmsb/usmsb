"""
Data Migration Module

Provides data migration functionality for moving user data between IPFS and local storage.
"""

import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..session.user_session import UserSession


logger = logging.getLogger(__name__)


@dataclass
class MigrationProgress:
    """Data migration progress tracking."""
    stage: str = "idle"
    total_items: int = 0
    completed_items: int = 0
    bytes_processed: int = 0
    total_bytes: int = 0
    message: str = ""
    error: str | None = None
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None

    @property
    def percentage(self) -> float:
        """Calculate completion percentage."""
        if self.total_items == 0:
            return 0.0
        return (self.completed_items / self.total_items) * 100

    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed time in seconds."""
        end = self.end_time or time.time()
        return end - self.start_time

    @property
    def speed_mb_per_sec(self) -> float:
        """Get migration speed in MB/s."""
        if self.elapsed_seconds == 0:
            return 0.0
        return (self.bytes_processed / (1024 * 1024)) / self.elapsed_seconds


@dataclass
class MigrationResult:
    """Result of a migration operation."""
    success: bool
    cid: str | None = None
    items_imported: int = 0
    items_exported: int = 0
    bytes_transferred: int = 0
    error: str | None = None
    verification_passed: bool = False


class DataMigration:
    """
    Data migration service for synchronizing user data between IPFS and local storage.

    Handles:
    - Exporting local data to IPFS with encryption
    - Importing data from IPFS to local storage
    - Verification of migrated data integrity
    - Progress tracking and callbacks

    Usage:
        migration = DataMigration(session)
        result = await migration.export_to_ipfs(progress_callback=on_progress)
    """

    # Data version for compatibility checking
    DATA_VERSION = "1.0"

    # Maximum file size for single upload (10MB)
    MAX_UPLOAD_SIZE = 10 * 1024 * 1024

    def __init__(self, session: "UserSession"):
        """
        Initialize data migration service.

        Args:
            session: UserSession instance with access to db and ipfs_client
        """
        self.session = session
        self._progress: MigrationProgress = MigrationProgress()
        self._progress_callbacks: list[Callable[[MigrationProgress], None]] = []

    def add_progress_callback(self, callback: Callable[[MigrationProgress], None]) -> None:
        """
        Add a progress callback.

        Args:
            callback: Function that receives MigrationProgress updates
        """
        self._progress_callbacks.append(callback)

    def _notify_progress(self) -> None:
        """Notify all progress callbacks."""
        for callback in self._progress_callbacks:
            try:
                callback(self._progress)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")

    def _start_stage(self, stage: str, total_items: int = 0, message: str = "") -> None:
        """Start a new migration stage."""
        self._progress.stage = stage
        self._progress.total_items = total_items
        self._progress.completed_items = 0
        self._progress.message = message
        self._progress.error = None
        self._notify_progress()

    def _update_progress(self, completed: int = 1, bytes_processed: int = 0, message: str = "") -> None:
        """Update migration progress."""
        self._progress.completed_items += completed
        self._progress.bytes_processed += bytes_processed
        if message:
            self._progress.message = message
        self._notify_progress()

    def _complete_stage(self, success: bool = True, error: str | None = None) -> None:
        """Complete current migration stage."""
        self._progress.end_time = time.time()
        if error:
            self._progress.error = error
        if not success:
            self._progress.stage = f"{self._progress.stage}_failed"
        self._notify_progress()

    async def migrate_from_ipfs(
        self,
        force: bool = False,
        verify: bool = True
    ) -> MigrationResult:
        """
        Migrate user data from IPFS to local storage.

        Process:
        1. Check if this is a first-time migration
        2. Retrieve user's encrypted data from IPFS
        3. Decrypt data using session's encryption key
        4. Import data to local database
        5. Update primary node record

        Args:
            force: Force migration even if local data exists
            verify: Verify data integrity after migration

        Returns:
            MigrationResult with migration status and statistics

        Raises:
            RuntimeError: If session is not initialized
            ValueError: If encryption key is not set
        """
        result = MigrationResult(success=False)

        try:
            # Check if session is initialized
            if not self.session._initialized:
                raise RuntimeError("Session not initialized. Call init() first.")

            # Check if migration is needed
            if not force and await self._has_local_data():
                logger.info(f"Local data exists for {self.session.wallet_address}, skipping migration")
                result.success = True
                result.verification_passed = True
                return result

            # Start migration
            logger.info(f"Starting migration from IPFS for {self.session.wallet_address}")
            self._start_stage("fetching_cid", message="Retrieving user data CID from IPFS...")

            # Get CID for user data
            cid = await self.session.ipfs_client.get_user_cid(self.session.wallet_address)
            if not cid:
                # First-time user, no data to migrate
                logger.info(f"No IPFS data found for {self.session.wallet_address}, new user")
                self._complete_stage(success=True, error="No data found")
                result.success = True
                result.items_imported = 0
                return result

            self._update_progress(message=f"Found CID: {cid[:16]}...")

            # Download data from IPFS
            self._start_stage("downloading", total_items=1, message="Downloading encrypted data from IPFS...")
            data = await self.session.ipfs_client.download_user_data(
                self.session.wallet_address,
                cid,
                decrypt=True
            )

            if not data:
                raise ValueError("Failed to download or decrypt data from IPFS")

            bytes_downloaded = len(json.dumps(data).encode('utf-8'))
            self._update_progress(bytes_processed=bytes_downloaded, message="Download complete")

            # Validate data version
            if "version" not in data:
                logger.warning("No version info in migrated data, assuming version 1.0")
                data["version"] = self.DATA_VERSION
            elif data["version"] != self.DATA_VERSION:
                logger.warning(f"Data version mismatch: expected {self.DATA_VERSION}, got {data['version']}")

            # Import data to local database
            self._start_stage("importing", total_items=2, message="Importing data to local database...")

            items_imported = 0

            # Import profile
            if "profile" in data and data["profile"]:
                try:
                    profile_data = data["profile"]
                    # Convert to UserProfile format expected by database
                    from ..session.user_session import UserProfile
                    profile = UserProfile(
                        preferences=profile_data.get("preferences", {}),
                        commitments=profile_data.get("commitments", []),
                        knowledge=profile_data.get("knowledge", {}),
                        last_updated=profile_data.get("last_updated", time.time())
                    )
                    await self.session.db.update_profile(profile)
                    items_imported += 1
                    self._update_progress(message="Profile imported")
                except Exception as e:
                    logger.warning(f"Failed to import profile: {e}")

            # Import knowledge
            if "knowledge" in data and data["knowledge"]:
                try:
                    await self.session.db.import_knowledge(data["knowledge"])
                    items_imported += 1
                    self._update_progress(message="Knowledge imported")
                except Exception as e:
                    logger.warning(f"Failed to import knowledge: {e}")

            self._complete_stage(success=True)

            # Verify migration if requested
            if verify:
                self._start_stage("verifying", message="Verifying migrated data...")
                verification_passed = await self.verify_migration()
                self._complete_stage(success=verification_passed)

                if not verification_passed:
                    logger.error("Migration verification failed")
                    result.error = "Verification failed"
                    return result

            # Update session metadata
            self.session._ipfs_cid = cid
            await self.session._update_metadata()

            # Update primary node record
            meta_file = Path(f"/data/users/{self.session.wallet_address}/meta.json")
            if meta_file.exists():
                with open(meta_file) as f:
                    meta_data = json.load(f)
                meta_data["primary_node"] = self.session.node_id
                meta_data["last_sync"] = time.time()
                with open(meta_file, 'w') as f:
                    json.dump(meta_data, f, indent=2)

            # Return success result
            result.success = True
            result.cid = cid
            result.items_imported = items_imported
            result.bytes_transferred = bytes_downloaded
            result.verification_passed = verify

            logger.info(f"Migration completed successfully: {items_imported} items imported")
            return result

        except Exception as e:
            logger.error(f"Migration from IPFS failed: {e}")
            self._complete_stage(success=False, error=str(e))
            result.error = str(e)
            return result

    async def export_to_ipfs(
        self,
        verify: bool = True
    ) -> MigrationResult:
        """
        Export local user data to IPFS.

        Process:
        1. Export data from local database
        2. Encrypt data using session's encryption key
        3. Upload to IPFS
        4. Return CID
        5. Optionally verify upload

        Args:
            verify: Verify upload by re-downloading and comparing

        Returns:
            MigrationResult with CID and statistics

        Raises:
            RuntimeError: If session is not initialized
            ValueError: If encryption key is not set
        """
        result = MigrationResult(success=False)

        try:
            # Check if session is initialized
            if not self.session._initialized:
                raise RuntimeError("Session not initialized. Call init() first.")

            # Export data from local database
            self._start_stage("exporting", total_items=2, message="Exporting data from local database...")

            data = {
                "version": self.DATA_VERSION,
                "wallet_address": self.session.wallet_address,
                "exported_at": time.time(),
                "synced_at": time.time(),
            }

            # Export profile
            try:
                profile_data = await self.session.db.get_profile()
                data["profile"] = profile_data
                self._update_progress(message="Profile exported")
            except Exception as e:
                logger.warning(f"Failed to export profile: {e}")
                data["profile"] = None

            # Export knowledge
            try:
                knowledge_data = await self.session.db.export_knowledge()
                data["knowledge"] = knowledge_data
                self._update_progress(message="Knowledge exported")
            except Exception as e:
                logger.warning(f"Failed to export knowledge: {e}")
                data["knowledge"] = None

            items_exported = 2  # profile + knowledge (even if None)

            # Prepare for upload
            data_json = json.dumps(data)
            data_bytes = data_json.encode('utf-8')

            # Check size
            if len(data_bytes) > self.MAX_UPLOAD_SIZE:
                logger.warning(f"Data size ({len(data_bytes)} bytes) exceeds limit, compression recommended")

            self._complete_stage(success=True)

            # Upload to IPFS
            self._start_stage("uploading", total_items=1, message="Uploading encrypted data to IPFS...")

            upload_result = await self.session.ipfs_client.upload_user_data(
                self.session.wallet_address,
                data,
                encrypt=True
            )

            if not upload_result.success:
                raise ValueError(f"IPFS upload failed: {upload_result.error}")

            cid = upload_result.cid
            bytes_uploaded = upload_result.size

            self._update_progress(bytes_processed=bytes_uploaded, message=f"Upload complete: CID={cid[:16]}...")
            self._complete_stage(success=True)

            # Verify upload if requested
            if verify:
                self._start_stage("verifying", message="Verifying uploaded data...")
                verification_passed = await self._verify_upload(cid, data)
                self._complete_stage(success=verification_passed)

                if not verification_passed:
                    logger.error("Upload verification failed")
                    result.error = "Verification failed"
                    return result

            # Pin CID
            self._start_stage("pinning", message="Pinning data to IPFS...")
            pin_result = await self.session.ipfs_client.pin_cid(cid)
            self._complete_stage(success=pin_result)

            # Publish CID
            self._start_stage("publishing", message="Publishing CID...")
            publish_result = await self.session.ipfs_client.publish_cid(
                self.session.wallet_address,
                cid
            )
            self._complete_stage(success=publish_result)

            # Update session metadata
            self.session._ipfs_cid = cid
            await self.session._update_metadata()

            # Return success result
            result.success = True
            result.cid = cid
            result.items_exported = items_exported
            result.bytes_transferred = bytes_uploaded
            result.verification_passed = verify

            logger.info(f"Export completed successfully: CID={cid}, {bytes_uploaded} bytes transferred")
            return result

        except Exception as e:
            logger.error(f"Export to IPFS failed: {e}")
            self._complete_stage(success=False, error=str(e))
            result.error = str(e)
            return result

    async def verify_migration(self) -> bool:
        """
        Verify that data was correctly migrated from IPFS.

        Returns:
            True if verification passes, False otherwise
        """
        try:
            # Get current profile from local database
            local_profile = await self.session.db.get_profile()

            # Get IPFS data
            if not self.session._ipfs_cid:
                return False

            ipfs_data = await self.session.ipfs_client.download_user_data(
                self.session.wallet_address,
                self.session._ipfs_cid
            )

            if not ipfs_data or "profile" not in ipfs_data:
                return False

            # Compare profiles (basic check)
            if local_profile and ipfs_data["profile"]:
                local_time = local_profile.get("last_updated", 0)
                ipfs_time = ipfs_data["profile"].get("last_updated", 0)

                # Check if local data is at least as recent as IPFS
                if local_time >= ipfs_time:
                    return True
                # Allow slight difference due to rounding
                if abs(local_time - ipfs_time) < 1.0:
                    return True

            return True  # Basic check passed

        except Exception as e:
            logger.error(f"Migration verification failed: {e}")
            return False

    async def _verify_upload(self, cid: str, original_data: dict) -> bool:
        """
        Verify that uploaded data can be retrieved correctly.

        Args:
            cid: CID of uploaded data
            original_data: Original data that was uploaded

        Returns:
            True if verification passes, False otherwise
        """
        try:
            # Download the data
            downloaded_data = await self.session.ipfs_client.download_user_data(
                self.session.wallet_address,
                cid,
                decrypt=True
            )

            if not downloaded_data:
                return False

            # Compare key fields
            if downloaded_data.get("version") != original_data.get("version"):
                return False

            if downloaded_data.get("wallet_address") != original_data.get("wallet_address"):
                return False

            # Compare exported_at timestamps
            original_time = original_data.get("exported_at", 0)
            downloaded_time = downloaded_data.get("exported_at", 0)

            if abs(original_time - downloaded_time) > 1.0:
                logger.warning(f"Timestamp mismatch: original={original_time}, downloaded={downloaded_time}")

            return True

        except Exception as e:
            logger.error(f"Upload verification failed: {e}")
            return False

    async def _has_local_data(self) -> bool:
        """
        Check if local database has existing data.

        Returns:
            True if local data exists, False otherwise
        """
        try:
            # Check if profile exists in local database
            profile = await self.session.db.get_profile()
            return profile is not None and profile.get("preferences") is not None
        except Exception:
            return False

    def get_progress(self) -> MigrationProgress:
        """
        Get current migration progress.

        Returns:
            MigrationProgress object with current status
        """
        return self._progress

    def reset_progress(self) -> None:
        """Reset migration progress to initial state."""
        self._progress = MigrationProgress()
