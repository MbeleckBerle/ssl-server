import pytest
import socket
import time
from collections import deque
from unittest.mock import patch, MagicMock
import logging
import server
import os
import tempfile
from server import search_string_in_file


# Helper: Custom exists_side_effect
def exists_side_effect(arg):
    if arg.strip() == "nonexistent.txt":
        return False
    return True


# Create a temporary file for testing
@pytest.fixture
def sample_file() -> str:
    with tempfile.NamedTemporaryFile(delete=False, mode="w",
                                     encoding="utf-8") as temp_file:
        temp_file.write("hello world\n")
        temp_file.write("python is awesome\n")
        temp_file.write("openai is cool\n")
        return temp_file.name


def test_search_string_found(sample_file: str) -> None:
    """Test case where the query exists in the file."""
    result = search_string_in_file(sample_file, "python is awesome")
    assert "STRING EXISTS, LINE" in result  # Updated assertion


def test_search_string_not_found(sample_file: str) -> None:
    """Test case where the query does not exist in the file."""
    result = search_string_in_file(sample_file, "not in file")
    assert result == "STRING NOT FOUND"


def test_empty_query(sample_file: str) -> None:
    """Test case for an empty query."""
    result = search_string_in_file(sample_file, "")
    assert result == "ERROR: EMPTY QUERY"


def test_long_query(sample_file: str) -> None:
    """Test case for a query exceeding MAX_QUERY_LENGTH."""
    long_query = "a" * 2000  # Exceeds MAX_QUERY_LENGTH (set to 1024)
    result = search_string_in_file(sample_file, long_query)
    assert result == "ERROR: QUERY TOO LONG"


def test_file_not_found() -> None:
    """Test case where the file does not exist."""
    result = search_string_in_file("non_existent.txt", "test")
    assert result == "ERROR: FILE NOT FOUND"


@pytest.fixture(scope="function", autouse=True)
def cleanup_files(sample_file: str):
    """Cleanup function to delete temp files after tests."""
    yield
    os.remove(sample_file)


# FakeSocket to simulate a client socket
class FakeSocket:
    def __init__(self, responses, raise_on_recv=None):
        self.responses = responses  # List of bytes to return on each call.
        self.sent = []
        self._closed = False
        self.raise_on_recv = raise_on_recv  # Exception to raise on recv if any

    def sendall(self, data):
        self.sent.append(data)

    def recv(self, bufsize):
        if self.raise_on_recv:
            raise self.raise_on_recv
        if self.responses:
            return self.responses.pop(0)
        return b""

    def settimeout(self, timeout):
        pass

    def close(self):
        self._closed = True

    @property
    def closed(self):
        return self._closed


# FakeServerSocket to simulate a server socket
class FakeServerSocket:
    def __init__(self, connections):
        self.connections = connections  # List of (FakeSocket, address) tuples.
        self.call_count = 0
        self.closed = False

    def setsockopt(self, *args, **kwargs):
        pass

    def bind(self, address):
        self.address = address

    def listen(self):
        pass

    def accept(self):
        if self.call_count < len(self.connections):
            conn, addr = self.connections[self.call_count]
            self.call_count += 1
            return conn, addr
        raise KeyboardInterrupt

    def close(self):
        self.closed = True


# Tests for load_config
@pytest.mark.parametrize(
    "config_path, get_side_effect, expected",
    [
        # Valid configuration
        (
            "valid_config.ini",
            ["test_file.txt", "False", "False", "", ""],
            ("test_file.txt", False, False, "", ""),
        ),
        # Invalid configuration: linuxpath is nonexistent
        (
            "invalid_config.ini",
            ["nonexistent.txt", "False", "False", "", ""],
            (None, False, False, None, None),
        ),
    ],
)
@patch("server.configparser.ConfigParser")
@patch("server.os.path.exists", side_effect=exists_side_effect)
def test_load_config(mock_exists, mock_config_parser, config_path,
                     get_side_effect, expected):
    mock_config = MagicMock()
    mock_config.read.return_value = None
    # When config["DEFAULT"].get is called, use side_effect.
    mock_config.__getitem__.return_value.get.side_effect = get_side_effect
    mock_config_parser.return_value = mock_config

    result = server.load_config(config_path)
    assert result == expected


@patch("server.os.path.exists", return_value=False)
def test_load_config_missing_file(mock_exists):
    result = server.load_config("missing_config.ini")
    assert result == (None, False, False, None, None)


# Tests for preprocess_file
@patch("server.open", create=True)
def test_preprocess_file_success(mock_open):
    file_content = ["line1\n", "line2\n", "line3\n"]
    mock_file = MagicMock()
    mock_file.__enter__.return_value = file_content
    mock_open.return_value = mock_file

    result = server.preprocess_file("dummy.txt")
    assert result == [(1, "line1"), (2, "line2"), (3, "line3")]


@patch("server.open", side_effect=Exception("File read error"))
def test_preprocess_file_failure(mock_open):
    result = server.preprocess_file("dummy.txt")
    assert result is None


# Test for sanitize_query
def test_sanitize_query():
    assert server.sanitize_query("   Hello   World   ") == "Hello World"


# Tests for search_string_in_file
@patch("server.os.path.exists", side_effect=exists_side_effect)
@patch("server.preprocess_file")
def test_search_string_in_file_found(mock_preprocess, mock_exists):
    mock_preprocess.return_value = [(1, "hello"), (2, "world")]
    server.REREAD_ON_QUERY = True
    result = server.search_string_in_file("dummy.txt", "hello")
    assert "STRING EXISTS, LINE" in result  # Updated assertion


@patch("server.os.path.exists", side_effect=exists_side_effect)
@patch("server.preprocess_file")
def test_search_string_in_file_not_found(mock_preprocess, mock_exists):
    mock_preprocess.return_value = [(1, "hello"), (2, "world")]
    server.REREAD_ON_QUERY = True
    result = server.search_string_in_file("dummy.txt", "foo")
    assert result == "STRING NOT FOUND"


@patch("server.os.path.exists", return_value=True)
def test_search_string_in_file_empty_query(mock_exists):
    result = server.search_string_in_file("dummy.txt", "")
    assert result == "ERROR: EMPTY QUERY"


@patch("server.os.path.exists", return_value=True)
def test_search_string_in_file_query_too_long(mock_exists):
    long_query = "a" * (server.MAX_QUERY_LENGTH + 1)
    result = server.search_string_in_file("dummy.txt", long_query)
    assert result == "ERROR: QUERY TOO LONG"


# New Tests for REREAD_ON_QUERY behavior
@patch("server.os.path.exists", return_value=True)
@patch("server.preprocess_file")
def test_reread_on_query_true(mock_preprocess, mock_exists):
    server.REREAD_ON_QUERY = True
    mock_preprocess.return_value = [(1, "a"), (2, "b"), (3, "c")]
    _ = server.search_string_in_file("dummy.txt", "a")
    _ = server.search_string_in_file("dummy.txt", "b")
    # Expect preprocess_file to be called twice when REREAD_ON_QUERY is True.
    assert mock_preprocess.call_count >= 2


@patch("server.os.path.exists", return_value=True)
@patch("server.preprocess_file")
def test_reread_on_query_false(mock_preprocess, mock_exists):
    server.REREAD_ON_QUERY = False
    server.cached_lines = None  # Clear cache
    mock_preprocess.return_value = [(1, "a"), (2, "b"), (3, "c")]
    _ = server.search_string_in_file("dummy.txt", "a")
    _ = server.search_string_in_file("dummy.txt", "b")
    # Expect preprocess_file to be called only once due to caching.
    assert mock_preprocess.call_count == 1


# Test for log_search
def test_log_search(caplog):
    with caplog.at_level(logging.INFO):
        test = 'test'
        ip = "127.0.0.1:12345"
        Execution_time = 100
        result = "STRING EXISTS, LINE 1"  # Updated result to match new format
        server.log_search(test, ip, 100, result)
    expected = (f"Query: '{test}', IP: {ip}, "
                f"Execution Time: {Execution_time}ms, Result: {result}")
    assert expected in caplog.text


# Tests for rate_limit_exceeded
def test_rate_limit_exceeded():
    addr = "127.0.0.1"
    server.client_requests[addr] = deque()
    now = time.time()
    for _ in range(server.RATE_LIMIT):
        server.client_requests[addr].append(now - (server.RATE_WINDOW - 1))
    # Next request should exceed the limit.
    assert server.rate_limit_exceeded(addr) is True


def test_rate_limit_not_exceeded():
    addr = "127.0.0.2"
    server.client_requests[addr] = deque()
    now = time.time()
    for _ in range(server.RATE_LIMIT - 1):
        server.client_requests[addr].append(now - (server.RATE_WINDOW - 1))
    assert server.rate_limit_exceeded(addr) is False


def test_rate_limit_reset():
    addr = "127.0.0.3"
    server.client_requests[addr] = deque()
    base_time = 1000.0
    for _ in range(server.RATE_LIMIT):
        server.client_requests[addr].append(base_time)
    with patch("server.time.time",
               return_value=base_time + server.RATE_WINDOW + 1):
        # After the rate window, the rate limit should reset.
        assert server.rate_limit_exceeded(addr) is False


# Tests for handle_client using FakeSocket
@patch("server.search_string_in_file",
       return_value="STRING EXISTS, LINE 1")  # Updated return value
def test_handle_client_valid_query(mock_search):
    # Force rate_limit_exceeded to always return False by patching it.
    with patch("server.rate_limit_exceeded", return_value=False):
        server.client_requests["127.0.0.1"] = deque()  # Clear IP rate limit
        fake_sock = FakeSocket([b"hello", b""])
        addr = ("127.0.0.1", 12345)
        server.handle_client(fake_sock, addr)
    sent_data = b"".join(fake_sock.sent)
    # Check for welcome message and valid query response.
    assert b"Hello, you are connected to the server!\n" in sent_data
    assert b"STRING EXISTS, LINE 1\n" in sent_data  # Updated assertion
    assert fake_sock.closed


@patch("server.rate_limit_exceeded", return_value=False)
def test_handle_client_empty_query(mock_rate_limit):
    fake_sock = FakeSocket([b"  ", b""])
    addr = ("127.0.0.1", 12345)
    server.handle_client(fake_sock, addr)
    sent_data = b"".join(fake_sock.sent)
    assert b"ERROR: EMPTY QUERY\n" in sent_data
    assert fake_sock.closed


def test_handle_client_exit():
    fake_sock = FakeSocket([b"exit"])
    addr = ("127.0.0.1", 12345)
    server.handle_client(fake_sock, addr)
    sent_data = b"".join(fake_sock.sent)
    assert b"Goodbye!\n" in sent_data
    assert fake_sock.closed


# New Tests for additional security measures in handle_client
def test_handle_client_input_too_large():
    # Simulate a client sending input that exceeds MAX_INCOMING_LENGTH.
    too_large_data = b"a" * (server.MAX_INCOMING_LENGTH + 1)
    fake_sock = FakeSocket([too_large_data])
    addr = ("127.0.0.1", 12345)
    server.handle_client(fake_sock, addr)
    sent_data = b"".join(fake_sock.sent)
    assert b"ERROR: Input data too large.\n" in sent_data
    assert fake_sock.closed


def test_handle_client_decode_error():
    # Simulate a client sending bytes that cannot be decoded.
    fake_sock = FakeSocket([b"\xff\xff"])
    addr = ("127.0.0.1", 12345)
    server.handle_client(fake_sock, addr)
    sent_data = b"".join(fake_sock.sent)
    assert b"ERROR: Unable to decode input.\n" in sent_data
    assert fake_sock.closed


def test_handle_client_timeout():
    # Simulate a timeout by having recv() raise a socket.timeout.
    fake_sock = FakeSocket([])
    fake_sock.settimeout = MagicMock()
    fake_sock.recv = MagicMock(side_effect=socket.timeout)
    addr = ("127.0.0.1", 12345)
    # When a timeout occurs, we expect an error log and connection closure.
    server.handle_client(fake_sock, addr)
    # No data is sent back because the exception is caught.
    assert fake_sock.closed


@pytest.fixture
def fake_server_socket():
    fake_conn = FakeSocket([b"exit"])
    fake_addr = ("127.0.0.1", 12345)
    return FakeServerSocket([(fake_conn, fake_addr)])


@patch("server.load_config",
       return_value=("dummy.txt", False, False, None, None))
@patch("server.preprocess_file", return_value=[(1, "hello"), (2, "world")])
@patch("server.socket.socket")
def test_start_server(mock_socket_class, mock_preprocess, mock_load_config,
                      fake_server_socket):
    # Force accept() to immediately raise\
    # KeyboardInterrupt to simulate shutdown.
    # helper for pep8 compliance
    def raise_keyboard_interrupt():
        raise KeyboardInterrupt()

    fake_server_socket.accept = lambda: raise_keyboard_interrupt()
    mock_socket_class.return_value = fake_server_socket

    server.start_server()
    assert fake_server_socket.closed is True


@patch("server.load_config",
       return_value=("dummy.txt", False, True, "cert.pem", "keyfile.pem"))
@patch("server.preprocess_file", return_value=[(1, "hello")])
@patch("server.socket.socket")
@patch("server.ssl.create_default_context")
def test_start_server_ssl_error(
    mock_create_default_context,
    mock_socket_class,
    mock_preprocess,
    mock_load_config,
    fake_server_socket
):
    def raise_keyboard_interrupt():
        raise KeyboardInterrupt()

    fake_server_socket.accept = raise_keyboard_interrupt
    mock_socket_class.return_value = fake_server_socket


@patch("server.socket.socket")
def test_server_shutdown(mock_socket_class):
    # helper for pep8 compliance
    def raise_keyboard_interrupt():
        raise KeyboardInterrupt()

    fake_server_socket = FakeServerSocket([])
    fake_server_socket.accept = lambda: raise_keyboard_interrupt()
    mock_socket_class.return_value = fake_server_socket
    server.start_server()
    assert fake_server_socket.closed is True
