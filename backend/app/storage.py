from functools import lru_cache

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import BlobServiceClient, ContentSettings

from .config import settings


class Storage:
    def upload(self, blob_name: str, data: bytes, content_type: str | None) -> None:
        raise NotImplementedError

    def download(self, blob_name: str) -> bytes:
        raise NotImplementedError

    def delete(self, blob_name: str) -> None:
        raise NotImplementedError


class AzureBlobStorage(Storage):
    def __init__(self, connection_string: str, container_name: str) -> None:
        if not connection_string:
            raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING no esta configurada")

        self._container = BlobServiceClient.from_connection_string(
            connection_string
        ).get_container_client(container_name)

        try:
            self._container.create_container()
        except ResourceExistsError:
            pass

    def upload(self, blob_name: str, data: bytes, content_type: str | None) -> None:
        content_settings = (
            ContentSettings(content_type=content_type) if content_type else None
        )
        self._container.get_blob_client(blob_name).upload_blob(
            data,
            overwrite=True,
            content_settings=content_settings,
        )

    def download(self, blob_name: str) -> bytes:
        return self._container.get_blob_client(blob_name).download_blob().readall()

    def delete(self, blob_name: str) -> None:
        try:
            self._container.get_blob_client(blob_name).delete_blob()
        except ResourceNotFoundError:
            pass


class InMemoryStorage(Storage):
    def __init__(self) -> None:
        self._blobs: dict[str, tuple[bytes, str | None]] = {}

    def upload(self, blob_name: str, data: bytes, content_type: str | None) -> None:
        self._blobs[blob_name] = (data, content_type)

    def download(self, blob_name: str) -> bytes:
        if blob_name not in self._blobs:
            raise KeyError(blob_name)
        return self._blobs[blob_name][0]

    def delete(self, blob_name: str) -> None:
        self._blobs.pop(blob_name, None)

    def clear(self) -> None:
        self._blobs.clear()


@lru_cache(maxsize=1)
def _build_storage() -> Storage:
    return AzureBlobStorage(
        settings.azure_storage_connection_string,
        settings.azure_storage_container,
    )


def get_storage() -> Storage:
    return _build_storage()
