import tempfile
from unittest.mock import MagicMock, patch
from client import run_client


@patch("client.ssl.create_default_context")
@patch("client.socket.socket")
def test_run_client_ssl(mock_socket, mock_create_default_context):
    """
    Test `run_client` when SSL is enabled and
    a valid server certificate is provided.

    This test simulates the scenario where SSL
    is enabled, the server certificate is valid,
    and the client successfully connects to the
    server using SSL.
    """
    config_content = """[DEFAULT]
    SSL_ENABLED=True
    SERVER_CERT={cert}
    """

    # Create a temporary certificate file
    with tempfile.NamedTemporaryFile(delete=False, mode="w",
                                     encoding="utf-8") as cert_file:
        cert_file.write("dummy certificate")
        cert_path = cert_file.name

    # Create a temporary configuration file
    with tempfile.NamedTemporaryFile(delete=False, mode="w",
                                     encoding="utf-8") as cfg:
        cfg.write(config_content.format(cert=cert_path))
        config_path = cfg.name

    fake_socket_instance = MagicMock()
    mock_socket.return_value = fake_socket_instance
    fake_socket_instance.recv.side_effect = [
        b"Welcome via SSL", b"SSL response"]

    fake_ssl_context = MagicMock()
    mock_create_default_context.return_value = fake_ssl_context

    # Ensure wrap_socket returns the same fake socket instance
    fake_ssl_context.wrap_socket.return_value = fake_socket_instance

    # Run the client with mocked input and print functions
    with patch("builtins.input", side_effect=[
                   "ssl query", "exit"
                   ]), patch("builtins.print") as mock_print:
        run_client("127.0.0.1", 44445, config_path)

    mock_print

    # Assert that the client attempted to connect
    fake_socket_instance.connect.assert_called_with(("127.0.0.1", 44445))


@patch("client.socket.socket")
def test_run_client_no_ssl(mock_socket):
    """
    Test `run_client` when SSL is disabled.

    This test simulates the scenario where
    SSL is disabled, and the client connects
    to the server without encryption.
    """
    config_content = """[DEFAULT]
    SSL_ENABLED=False
    """

    # Create a temporary configuration file
    with tempfile.NamedTemporaryFile(delete=False, mode="w",
                                     encoding="utf-8") as cfg:
        cfg.write(config_content)
        config_path = cfg.name

    fake_socket_instance = MagicMock()
    mock_socket.return_value = fake_socket_instance
    fake_socket_instance.recv.side_effect = [b"Welcome", b"Response"]

    # Run the client with mocked input and print functions
    with patch("builtins.input", side_effect=["test query", "exit"]), \
        patch("builtins.print") as mock_print:
        run_client("127.0.0.1", 44445, config_path)

    # Ensure mock_print is used to prevent linting warnings
    assert mock_print

    # Assert that the client attempted to connect
    fake_socket_instance.connect.assert_called_with(("127.0.0.1", 44445))


@patch("client.socket.socket")
def test_run_client_server_not_running(mock_socket):
    """
    Test `run_client` handling a connection refused error.

    This test simulates the scenario where the server is
    not running, and a `ConnectionRefusedError` is raised
    when attempting to connect.
    """
    config_content = """[DEFAULT]
    SSL_ENABLED=False
    """

    # Create a temporary configuration file
    with tempfile.NamedTemporaryFile(delete=False, mode="w",
                                     encoding="utf-8") as cfg:
        cfg.write(config_content)
        config_path = cfg.name

    fake_socket_instance = MagicMock()
    mock_socket.return_value = fake_socket_instance
    fake_socket_instance.connect.side_effect = ConnectionRefusedError

    # Run the client with mocked print function
    with patch("builtins.print") as mock_print:
        run_client("127.0.0.1", 44445, config_path)

    # Assert that the connection refused message is printed
    mock_print.assert_any_call("Connection refused. Is the server running?")
