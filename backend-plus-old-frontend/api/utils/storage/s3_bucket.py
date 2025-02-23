import os
import logging
from pathlib import Path
import boto3
from botocore.exceptions import ClientError, BotoCoreError

logger = logging.getLogger(__name__)

class S3Manager:
    def __init__(self):
        logger.info("Initializing S3 Manager...")
        self.bucket_name = os.getenv("S3_BUCKET_NAME")
        if self.bucket_name:
            logger.info(f"Found S3 bucket configuration: {self.bucket_name}")
        else:
            logger.info("No S3 bucket configured - S3 operations will be disabled")
        self._client = None
        self._init_client()

    def _init_client(self):
        """Initialize S3 client if credentials are available"""
        if not self.bucket_name:
            logger.info("S3 bucket name not configured - S3 operations disabled")
            return

        try:
            self._client = boto3.client('s3')
            # Test connection with a head bucket call
            self._client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Successfully connected to S3 bucket: {self.bucket_name}")
        except (ClientError, BotoCoreError) as e:
            logger.warning(f"Could not initialize S3 client: {e}")
            self._client = None

    def download_file(self, s3_key: str, local_path: Path) -> bool:
        """Download file from S3 with graceful failure"""
        if not self._client:
            return False

        try:
            self._client.download_file(
                self.bucket_name,
                s3_key,
                str(local_path)
            )
            logger.info(f"Successfully downloaded {s3_key} from S3")
            return True
        except ClientError as e:
            logger.warning(f"Could not download {s3_key} from S3: {e}")
            return False

    def upload_file(self, local_path: Path, s3_key: str) -> bool:
        """Upload file to S3 with graceful failure"""
        if not self._client:
            return False

        try:
            self._client.upload_file(
                str(local_path),
                self.bucket_name,
                s3_key
            )
            logger.info(f"Successfully uploaded {local_path} to S3")
            return True
        except ClientError as e:
            logger.warning(f"Could not upload {local_path} to S3: {e}")
            return False

# Global instance
s3_manager = S3Manager() 