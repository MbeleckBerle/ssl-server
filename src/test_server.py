import pytest
import server
import os
import socket
import ssl
import time
from datetime import datetime
from collections import defaultdict
from unittest.mock import patch, mock_open, MagicMock, call

@patch("server.log_search")
def test_load_config(mock_log_search):
    with open("test_config.ini", "w") as f:
        f.write("""
            [DEFAULT]
            linuxpath = test_file.txt
            REREAD_ON_QUERY = True
            SSL_ENABLED = True
            CERTFILE = test_cert.pem
            KEYFILE = test_key.pem
        """)
    with open("test_file.txt", "w") as f:
        f.write("test line\n")
    with open("test_cert.pem", "w") as f:
        f.write("cert")
    with open("test_key.pem", "w") as f:
        f.write("key")

    path, reread, ssl_enabled, certfile, keyfile = server.load_config("test_config.ini")
    assert path == "test_file.txt"
    assert reread is True
    assert ssl_enabled is True
    assert certfile == "test_cert.pem"
    assert keyfile == "test_key.pem"

    os.remove("test_config.ini")
    os.remove("test_file.txt")
    os.remove("test_cert.pem")
    os.remove("test_key.pem")

    path, _, _, _, _ = server.load_config("test_config.ini")
    assert path is None

    with open("test_config.ini", "w") as f:
        f.write("[DEFAULT]\nlinuxpath = non_existent_file.txt")
    path, _, _, _, _ = server.load_config("test_config.ini")
    assert path is None

    with open("test_config.ini", "w") as f:
        f.write("[DEFAULT]\nlinuxpath = test_file.txt\nREREAD_ON_QUERY = invalid")
    path, reread, _, _, _ = server.load_config("test_config.ini")
    assert reread is False

    with open("test_config.ini", "w") as f:
        f.write("[DEFAULT]\nlinuxpath = test_file.txt\nSSL_ENABLED = True")
    path, _, _, _, _ = server.load_config("test_config.ini")
    assert path is None
    os.remove("test_config.ini")



@patch("server.log_search")
def test_preprocess_file(mock_log_search):
    with open("test_file.txt", "w") as f:
        f.write(" line1 \nline2\n line3 ")
    lines = server.preprocess_file("test_file.txt")
    assert lines == {"line1", "line2", "line3"}
    os.remove("test_file.txt")
    assert server.preprocess_file("non_existent_file.txt") is None

@patch("server.log_search")
def test_sanitize_query(mock_log_search):
    assert server.sanitize_query("  test  query  ") == "test query"
    assert server.sanitize_query("test\tquery") == "test query"

@patch("server.log_search")
@patch("server.datetime")
def test_log_search(mock_datetime, mock_log_search):
    mock_datetime.now.return_value.strftime.return_value = "2024-01-01 00:00:00"
    server.log_search("test query", "127.0.0.1", 10, "STRING EXISTS")
    mock_log_search.assert_called_once_with("test query", "127.0.0.1", 10, "STRING EXISTS")
    with patch("builtins.open", side_effect=Exception("Mocked error")):
      server.log_search("test query", "127.0.0.1", 10, "STRING EXISTS")

@patch("server.log_search")
def test_rate_limit_exceeded(mock_log_search):
    addr = "127.0.0.1"
    server.client_requests = defaultdict(list)
    for _ in range(server.RATE_LIMIT):
        assert not server.rate_limit_exceeded(addr)
    assert server.rate_limit_exceeded(addr)
    time.sleep(server.RATE_WINDOW + 1)
    assert not server.rate_limit_exceeded(addr)


@patch("server.log_search")
@patch("server.search_string_in_file")
@patch("server.socket.socket")
def test_handle_client(mock_socket, mock_search_string, mock_log_search):
    mock_server_socket = mock_socket.return_value
    mock_conn = MagicMock()
    mock_server_socket.accept.return_value = (mock_conn, ("127.0.0.1", 12345))

    mock_search_string.return_value = "STRING EXISTS"

    mock_conn.recv.side_effect = [
        b"test query\n",
        b"exit\n",
        b"",
    ]
    mock_conn.sendall.return_value = None

    server.path = "test_file.txt"
    server.handle_client(mock_conn, ("127.0.0.1", 12345))

    calls = [c[0][0] for c in mock_conn.sendall.call_args_list]
    assert b"Hello, you are connected to the server!\n" in calls
    assert b"STRING EXISTS\n" in calls

    mock_conn.recv.side_effect = [b" \n", b"exit\n", b""]
    server.handle_client(mock_conn, ("127.0.0.1", 12345))
    calls = [c[0][0] for c in mock_conn.sendall.call_args_list]
    assert b"ERROR: EMPTY QUERY\n" in calls

    mock_conn.recv.side_effect = [b"test query\n"] * (server.RATE_LIMIT + 1) + [b"exit\n", b""]
    server.client_requests["127.0.0.1"] = []
    server.handle_client(mock_conn, ("127.0.0.1", 12345))
    calls = [c[0][0] for c in mock_conn.sendall.call_args_list]
    assert b"ERROR: RATE LIMIT EXCEEDED\n" in calls

    mock_conn.recv.side_effect = [ConnectionResetError]
    server.handle_client(mock_conn, ("127.0.0.1", 12345))

    mock_conn.recv.side_effect = [Exception("Mocked client error")]
    server.handle_client(mock_conn, ("127.0.0.1", 12345))


@patch("server.log_search")
def test_search_string_in_file(mock_log_search):
    with open("test_file.txt", "w") as f:
        f.write("test line\n")
    server.cached_lines = server.preprocess_file("test_file.txt")
    assert server.search_string_in_file("test_file.txt", "test line") == "STRING EXISTS"
    assert server.search_string_in_file("test_file.txt", "nonexistent line") == "STRING NOT FOUND"
    assert server.search_string_in_file("test_file.txt", "") == "ERROR: EMPTY QUERY"
    assert server.search_string_in_file("test_file.txt", "a" * 2000) == "ERROR: QUERY TOO LONG"
    os.remove("test_file.txt")
    server.cached_lines = None


@patch("server.log_search")
def test_preprocess_file_errors(mock_log_search):
    with open("test_file.txt", "w") as f:
        f.write("test line\n")

    os.chmod("test_file.txt", 0o000)  # Remove all permissions
    assert server.preprocess_file("test_file.txt") is None  # Expect None due to permission error
    os.chmod("test_file.txt", 0o777)  # Restore permissions

    with open("test_file.txt", "wb") as f:  # Write bytes for encoding error
        f.write(b"\xff\xfe\x00\x00") # Invalid UTF-16
    assert server.preprocess_file("test_file.txt") is None  # Expect None due to encoding error

    os.remove("test_file.txt")

    # Test file that does not exist
    assert server.preprocess_file("non_existent_file.txt") is None

    # Test OSError
    with patch("builtins.open", side_effect=OSError("Mocked OSError")):
        assert server.preprocess_file("test_file.txt") is None


@patch("server.log_search")
def test_load_config_errors(mock_log_search):

    with open("test_config.ini", "w") as f:
        f.write("""
            [DEFAULT]
            linuxpath = test_file.txt
            REREAD_ON_QUERY = True
            SSL_ENABLED = True
            CERTFILE = test_cert.pem
            KEYFILE = test_key.pem
            linuxpath = another_path.txt # duplicate key
        """)

    path, _, _, _, _ = server.load_config("test_config.ini")
    assert path is None

    os.remove("test_config.ini")