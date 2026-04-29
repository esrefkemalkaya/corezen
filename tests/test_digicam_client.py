"""digicam_client.py için testler. requests_mock ile HTTP simülasyonu."""
from __future__ import annotations

import pytest
import requests
import requests_mock as rm_lib

from karotcam.camera.digicam_client import (
    CameraConnectionError,
    DigiCamHTTPClient,
    MockDigiCamClient,
)

BASE = "http://localhost:5513"


def test_ping_returns_true_on_success(requests_mock: rm_lib.Mocker) -> None:
    requests_mock.get(f"{BASE}/?slc=get&param1=lastfile", text="ok")
    client = DigiCamHTTPClient(base_url=BASE, timeout_s=1)
    assert client.ping() is True


def test_ping_returns_false_on_connection_error(requests_mock: rm_lib.Mocker) -> None:
    requests_mock.get(
        f"{BASE}/?slc=get&param1=lastfile",
        exc=requests.exceptions.ConnectionError,
    )
    client = DigiCamHTTPClient(base_url=BASE, timeout_s=1)
    assert client.ping() is False


def test_ping_returns_false_on_timeout(requests_mock: rm_lib.Mocker) -> None:
    requests_mock.get(
        f"{BASE}/?slc=get&param1=lastfile",
        exc=requests.exceptions.Timeout,
    )
    client = DigiCamHTTPClient(base_url=BASE, timeout_s=1)
    assert client.ping() is False


def test_capture_raises_on_http_error(requests_mock: rm_lib.Mocker) -> None:
    requests_mock.get(f"{BASE}/?slc=capture&param1=&param2=", status_code=500)
    client = DigiCamHTTPClient(base_url=BASE, timeout_s=1)
    with pytest.raises(CameraConnectionError):
        client.capture()


def test_capture_raises_on_connection_error(requests_mock: rm_lib.Mocker) -> None:
    requests_mock.get(
        f"{BASE}/?slc=capture&param1=&param2=",
        exc=requests.exceptions.ConnectionError,
    )
    client = DigiCamHTTPClient(base_url=BASE, timeout_s=1)
    with pytest.raises(CameraConnectionError):
        client.capture()


def test_capture_succeeds_on_200(requests_mock: rm_lib.Mocker) -> None:
    requests_mock.get(f"{BASE}/?slc=capture&param1=&param2=", text="OK")
    client = DigiCamHTTPClient(base_url=BASE, timeout_s=1)
    client.capture()  # raises nothing


def test_set_session_folder(requests_mock: rm_lib.Mocker) -> None:
    requests_mock.get(
        f"{BASE}/?slc=set&param1=session.folder&param2=C:/x",
        text="OK",
    )
    client = DigiCamHTTPClient(base_url=BASE, timeout_s=1)
    client.set_session_folder("C:/x")


def test_get_liveview_jpeg_returns_bytes(requests_mock: rm_lib.Mocker) -> None:
    payload = b"\xff\xd8\xff\xe0fakejpeg"
    requests_mock.get(f"{BASE}/liveview.jpg", content=payload)
    client = DigiCamHTTPClient(base_url=BASE, timeout_s=1)
    assert client.get_liveview_jpeg() == payload


def test_get_liveview_jpeg_returns_none_on_error(requests_mock: rm_lib.Mocker) -> None:
    requests_mock.get(
        f"{BASE}/liveview.jpg", exc=requests.exceptions.ConnectionError
    )
    client = DigiCamHTTPClient(base_url=BASE, timeout_s=1)
    assert client.get_liveview_jpeg() is None


def test_mock_client_ping_true_capture_no_raise() -> None:
    client = MockDigiCamClient()
    assert client.ping() is True
    client.capture()  # no raise
    client.set_session_folder("C:/x")
    assert client.get_liveview_jpeg() == b""
