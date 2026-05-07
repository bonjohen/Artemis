"""Tests for the download module."""

from unittest.mock import MagicMock, patch

import pytest

from artemis_calendar.extract.download import DownloadError, DownloadResult, download_artifact


def test_download_result_checksum():
    result = DownloadResult(
        content=b"hello world",
        status_code=200,
        headers={},
        downloaded_at="2026-01-01T00:00:00Z",
        url="https://example.com/test",
    )
    checksum = result.compute_checksum()
    assert len(checksum) == 64  # SHA-256 hex digest
    assert checksum == result.checksum


@patch("artemis_calendar.extract.download.httpx.Client")
def test_download_success(mock_client_cls):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"test content"
    mock_response.headers = {"content-type": "text/plain"}

    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client_cls.return_value = mock_client

    result = download_artifact("https://example.com/test", max_retries=0)
    assert result.content == b"test content"
    assert result.status_code == 200
    assert len(result.checksum) == 64


@patch("artemis_calendar.extract.download.httpx.Client")
def test_download_404_raises(mock_client_cls):
    mock_response = MagicMock()
    mock_response.status_code = 404

    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client_cls.return_value = mock_client

    with pytest.raises(DownloadError) as exc_info:
        download_artifact("https://example.com/missing", max_retries=0)
    assert exc_info.value.status_code == 404
