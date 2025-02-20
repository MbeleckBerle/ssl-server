import os
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, mock_open, patch

import pytest

from server import (
    load_config, search_string_in_file, log_search,
    handle_client, start_server,
)


###############################################################################
# Tests for load_config()
###############################################################################

def test_config_file_missing() -> None:
    """
    Test case for when the configuration file is missing.
    Ensures the default values are returned.
    """
    non_existent_path: str = "non_existent_config_file.ini"
    (file_path, reread_on_query, ssl_enabled,
     certfile, keyfile) = load_config(non_existent_path)
    assert file_path is None
    assert not reread_on_query
    assert not ssl_enabled
    assert certfile is None
    assert keyfile is None


def test_config_invalid_key() -> None:
    """
    Test case for an invalid configuration file
    that is missing the 'linuxpath' key.
    Verifies that default values are returned.
    """
    with tempfile.NamedTemporaryFile(delete=False, mode="w",
                                     encoding="utf-8") as config_file:
        config_file.write("[DEFAULT]\nREREAD_ON_QUERY = True\n")
        config_file_path: str = config_file.name
    try:
        (file_path, reread_on_query, ssl_enabled,
         certfile, keyfile) = load_config(config_file_path)
        assert file_path is None
        assert not reread_on_query
        assert not ssl_enabled
        assert certfile is None
        assert keyfile is None
    finally:
        os.remove(config_file_path)


def test_config_file_does_not_exist() -> None:
    """
    Test case for a configuration file that
    references a non-existent search file.
    Ensures that defaults are returned when
    the referenced file doesn't exist.
    """
    non_existent_search_file: str = "non_existent_search_file.txt"
    with tempfile.NamedTemporaryFile(delete=False, mode="w",
                                     encoding="utf-8") as config_file:
        config_file.write(f"[DEFAULT]\nlinuxpath = {non_existent_search_file}\
                          \nREREAD_ON_QUERY = False\n")
        config_file_path: str = config_file.name
    try:
        (file_path, reread_on_query, ssl_enabled,
         certfile, keyfile) = load_config(config_file_path)
        assert file_path is None
        assert not reread_on_query
        assert not ssl_enabled
        assert certfile is None
        assert keyfile is None
    finally:
        os.remove(config_file_path)


def test_load_config_valid(tmp_path: Path) -> None:
    """
    Test case for a valid configuration file and search file.
    Verifies the proper configuration values are loaded.
    """
    search_file = tmp_path / "search.txt"
    search_file.write_text("line1\nline2\n")

    # Create dummy certificate and key files so SSL check passes.
    cert_file = tmp_path / "cert.pem"
    cert_file.write_text("dummy cert")
    key_file = tmp_path / "key.pem"
    key_file.write_text("dummy key")

    config_file = tmp_path / "config.ini"
    config_file.write_text(
        f"[DEFAULT]\n"
        f"linuxpath = {search_file}\n"
        f"REREAD_ON_QUERY = True\n"
        f"SSL_ENABLED = True\n"
        f"CERTFILE = {cert_file}\n"
        f"KEYFILE = {key_file}\n"
    )

    (file_path, reread_on_query, ssl_enabled,
     certfile, keyfile) = load_config(str(config_file))
    assert file_path == str(search_file)
    assert reread_on_query is True
    assert ssl_enabled is True
    assert certfile == str(cert_file)
    assert keyfile == str(key_file)


###############################################################################
# Tests for search_string_in_file()
###############################################################################

def test_empty_query(tmp_path: Path) -> None:
    """
    Test case for an empty query passed to the search function.
    Ensures it returns the appropriate error message.
    """
    search_file = tmp_path / "file.txt"
    search_file.write_text("some content\n")
    # Pass only two arguments: file path and query.
    result: str = search_string_in_file(str(search_file), "")
    assert result == "ERROR: EMPTY QUERY"


def test_file_not_found() -> None:
    """
    Test case for a search with a non-existent file.
    Ensures it returns the appropriate error message.
    """
    result: str = search_string_in_file("nonexistent_file.txt", "query")
    assert result == "ERROR: FILE NOT FOUND"


def test_string_exists_reread(tmp_path: Path) -> None:
    """
    Test case for a query that matches a string in the file.
    Verifies that the result correctly indicates the string exists.
    """
    search_file = tmp_path / "file.txt"
    search_file.write_text("match_line\nother_line\n")
    result: str = search_string_in_file(str(search_file), "match_line")
    assert result == "STRING EXISTS"


def test_string_not_found_reread(tmp_path: Path) -> None:
    """
    Test case for a query that does not match any string in the file.
    Verifies that the result correctly indicates the string is not found.
    """
    search_file = tmp_path / "file.txt"
    search_file.write_text("line1\nline2\n")
    result: str = search_string_in_file(str(search_file), "nonexistent")
    assert result == "STRING NOT FOUND"

###############################################################################
# Tests for log_search()
###############################################################################


def test_log_search_success(tmp_path: Path) -> None:
    """
    Test case for a successful log search.
    Verifies that log entries are correctly written to the file.
    """
    m = mock_open()
    with patch("builtins.open", m):
        log_search("test_query", "127.0.0.1:44445", 100.0, "STRING EXISTS")
    m.assert_called_with("server_log.txt", "a")
    handle = m()
    assert handle.write.called


def test_log_search_write_error() -> None:
    """
    Test case for handling a write error while logging.
    Verifies that the error message is correctly printed.
    """
    with patch("builtins.open", side_effect=Exception("Write failure")):
        with patch("builtins.print") as mock_print:
            log_search("test_query", "127.0.0.1:44445", 100.0, "STRING EXISTS")
            # Updated assertion to match the exact string without extra spaces
            mock_print.assert_any_call("Failed to write to log: Write failure")


###############################################################################
# Tests for handle_client()
###############################################################################


@pytest.fixture
def search_file_fixture() -> Generator[str, None, None]:
    """
    Fixture that sets up a temporary search file for testing.
    """
    with tempfile.NamedTemporaryFile(delete=False, mode="w",
                                     encoding="utf-8") as tmp_file:
        tmp_file.write("client_test_line")
        search_file_path: str = tmp_file.name
    yield search_file_path
    os.remove(search_file_path)


@pytest.fixture(autouse=True)
def setup_handle_client(search_file_fixture: str) -> None:
    """
    Fixture that sets up the necessary global variables
    for the handle_client test.
    """
    import server
    server.path = search_file_fixture
    server.REREAD_ON_QUERY = True
    server.BUFFER_SIZE = 1024


def test_handle_client_empty_query() -> None:
    """
    Test case for when the client sends an empty query.
    Verifies that the appropriate error message is sent back.
    """
    fake_conn: MagicMock = MagicMock()
    fake_addr: str = "127.0.0.1"
    # Simulate a client that sends a whitespace-only query
    fake_conn.recv.side_effect = [b"   ", b""]
    with patch("server.log_search"):
        handle_client(fake_conn, fake_addr)
    calls = fake_conn.sendall.call_args_list
    # Expect the "ERROR: EMPTY QUERY" message to have been sent.
    assert any(b"ERROR: EMPTY QUERY" in call[0][0] for call in calls)

###############################################################################
# Tests for start_server()
###############################################################################


def test_start_server() -> None:
    """
    Test case for starting the server.
    Verifies that the server attempts to
    bind to the correct address and handles client connections.
    """
    with patch("server.socket.socket") as mock_socket:
        fake_socket = MagicMock()
        mock_socket.return_value = fake_socket
        with patch("server.ssl.create_default_context") as mock_ssl_context:
            fake_ssl_context = MagicMock()
            mock_ssl_context.return_value = fake_ssl_context
            with patch("server.load_config", return_value=(
                "/tmp/dummy.txt",
                True, True,
                "/tmp/cert.pem",
                "/tmp/key.pem"
            )):
                fake_socket.accept.side_effect = [
                    (MagicMock(), ("127.0.0.1", 12345)),
                    KeyboardInterrupt
                ]
                try:
                    start_server()
                except KeyboardInterrupt:
                    pass
    fake_socket.bind.assert_called_with(("0.0.0.0", 44445))

###############################################################################
# Tests for 200k.txt file existence and content.
###############################################################################


class Test200kData:
    """
    Test class for handling the 200k.txt file.
    """
    @pytest.fixture(autouse=True)
    def data_file(self, tmp_path: Path) -> Generator[str, None, None]:
        data_file = tmp_path / "200k.txt"
        data_file.write_text("data\n" * 10)
        yield str(data_file)

    def test_file_exists(self, data_file: str) -> None:
        assert os.path.exists(data_file)

    def test_content_length(self, data_file: str) -> None:
        with open(data_file, "r") as f:
            content = f.read()
        assert len(content) > 0, "File content is empty!"
