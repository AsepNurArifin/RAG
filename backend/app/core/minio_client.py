"""
MinIO storage client — EnterpriseMind AI.
Replaces Google Drive client for local/self-hosted deployment.
"""
import logging
from datetime import timedelta
from minio import Minio
from app.core.config import settings

logger = logging.getLogger(__name__)

class MinIOClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MinIOClient, cls).__new__(cls)
            cls._instance._client = None
            cls._instance._initialized = False
        return cls._instance

    @property
    def client(self) -> Minio:
        if not self._initialized:
            self._client = self._init_client()
            self._initialized = True
        return self._client

    def _init_client(self) -> Minio:
        endpoint = settings.MINIO_ENDPOINT
        # Standard MinIO library expects hostname:port, strip protocol prefixes
        secure = False
        if endpoint.startswith("https://"):
            endpoint = endpoint[8:]
            secure = True
        elif endpoint.startswith("http://"):
            endpoint = endpoint[7:]

        logger.info("Initializing MinIO client: endpoint=%s, secure=%s", endpoint, secure)
        client = Minio(
            endpoint,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=secure,
        )
        
        # Ensure the bucket exists
        bucket_name = settings.MINIO_BUCKET_DOCS
        try:
            if not client.bucket_exists(bucket_name):
                logger.info("Creating MinIO bucket: %s", bucket_name)
                client.make_bucket(bucket_name)
            else:
                logger.debug("MinIO bucket '%s' already exists.", bucket_name)
        except Exception as e:
            logger.error("Failed to check/create MinIO bucket '%s': %s", bucket_name, e)
            
        return client

    def upload_file(self, file_path: str, object_name: str, content_type: str) -> str:
        """Upload file to MinIO and return object_name."""
        bucket_name = settings.MINIO_BUCKET_DOCS
        logger.info("Uploading %s to MinIO bucket %s as %s...", file_path, bucket_name, object_name)
        self.client.fput_object(
            bucket_name=bucket_name,
            object_name=object_name,
            file_path=file_path,
            content_type=content_type,
        )
        logger.info("Successfully uploaded %s to MinIO.", object_name)
        return object_name

    def download_file(self, object_name: str, local_dest: str) -> str:
        """Download file from MinIO to local destination."""
        bucket_name = settings.MINIO_BUCKET_DOCS
        logger.info("Downloading %s from MinIO bucket %s to %s...", object_name, bucket_name, local_dest)
        self.client.fget_object(
            bucket_name=bucket_name,
            object_name=object_name,
            file_path=local_dest,
        )
        logger.info("Successfully downloaded %s from MinIO.", object_name)
        return local_dest

    def delete_file(self, object_name: str):
        """Delete file from MinIO."""
        bucket_name = settings.MINIO_BUCKET_DOCS
        logger.info("Deleting %s from MinIO bucket %s...", object_name, bucket_name)
        try:
            self.client.remove_object(
                bucket_name=bucket_name,
                object_name=object_name,
            )
            logger.info("Successfully deleted %s from MinIO.", object_name)
        except Exception as e:
            logger.exception("Failed to delete %s from MinIO: %s", object_name, e)

    def get_presigned_url(self, object_name: str, expires_seconds: int = 3600) -> str:
        """
        Generate presigned GET URL untuk mengakses object (file asli) dari MinIO.

        Args:
            object_name: Object key di MinIO (mis. 'documents/{uuid}.pdf').
            expires_seconds: Masa berlaku URL dalam detik (default 1 jam).

        Returns:
            URL presigned yang bisa dibuka langsung di browser/tab baru.
        """
        bucket_name = settings.MINIO_BUCKET_DOCS
        try:
            url = self.client.presigned_get_object(
                bucket_name=bucket_name,
                object_name=object_name,
                expires=timedelta(seconds=expires_seconds),
            )
            logger.info("Generated presigned URL untuk %s (expires=%ds)", object_name, expires_seconds)
            return url
        except Exception as e:
            logger.exception("Gagal generate presigned URL untuk %s: %s", object_name, e)
            raise

minio_client = MinIOClient()
