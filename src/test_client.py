import tempfile
import os
import pytest
from unittest.mock import MagicMock, patch
from client import run_client  # Ensure this correctly imports your client module


@patch("client.ssl.create_default_context")
@patch("client.socket.socket")
def test_run_client_ssl(mock_socket, mock_create_default_context):
    """
    Test run_client when SSL is enabled and a valid server certificate is provided.
    """
    config_content = """[DEFAULT]
    SSL_ENABLED=True
    SERVER_CERT={cert}
    """

    with tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8") as cert_file:
        cert_file.write("dummy certificate")
        cert_path = cert_file.name

    with tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8") as cfg:
        cfg.write(config_content.format(cert=cert_path))
        config_path = cfg.name

    fake_socket_instance = MagicMock()
    mock_socket.return_value = fake_socket_instance
    fake_socket_instance.recv.side_effect = [b"Welcome via SSL", b"SSL response"]

    fake_ssl_context = MagicMock()
    mock_create_default_context.return_value = fake_ssl_context

    # Ensure wrap_socket returns the same fake socket instance
    fake_ssl_context.wrap_socket.return_value = fake_socket_instance

    with patch("builtins.input", side_effect=["ssl query", "exit"]), patch("builtins.print") as mock_print:
        run_client("127.0.0.1", 44446, config_path)

    # Assert that the client attempted to connect
    fake_socket_instance.connect.assert_called_with(("127.0.0.1", 44446))


@patch("client.socket.socket")
def test_run_client_no_ssl(mock_socket):
    """
    Test run_client when SSL is disabled.
    """
    config_content = """[DEFAULT]
    SSL_ENABLED=False
    """

    with tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8") as cfg:
        cfg.write(config_content)
        config_path = cfg.name

    fake_socket_instance = MagicMock()
    mock_socket.return_value = fake_socket_instance
    fake_socket_instance.recv.side_effect = [b"Welcome", b"Response"]

    with patch("builtins.input", side_effect=["test query", "exit"]), patch("builtins.print") as mock_print:
        run_client("127.0.0.1", 44446, config_path)

    fake_socket_instance.connect.assert_called_with(("127.0.0.1", 44446))


@patch("client.socket.socket")
def test_run_client_server_not_running(mock_socket):
    """
    Test run_client handling a connection refused error.
    """
    config_content = """[DEFAULT]
    SSL_ENABLED=False
    """

    with tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8") as cfg:
        cfg.write(config_content)
        config_path = cfg.name

    fake_socket_instance = MagicMock()
    mock_socket.return_value = fake_socket_instance
    fake_socket_instance.connect.side_effect = ConnectionRefusedError

    with patch("builtins.print") as mock_print:
        run_client("127.0.0.1", 44446, config_path)

    mock_print.assert_any_call("Connection refused. Is the server running?")
