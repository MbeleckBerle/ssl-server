import os
import socket
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, mock_open, patch

import pytest

from server import (
    load_config,
    search_string_in_file,
    search_string_in_file_cached,
    log_search,
    handle_client,
    start_server,
)


###############################################################################
# Tests for load_config()
###############################################################################

def test_config_file_missing() -> None:
    # Use a non-existent file path
    non_existent_path: str = "non_existent_config_file.ini"
    file_path, reread_on_query, ssl_enabled, certfile, keyfile = load_config(non_existent_path)
    assert file_path is None
    assert not reread_on_query
    assert not ssl_enabled
    assert certfile is None
    assert keyfile is None


def test_config_invalid_key() -> None:
    # Create a config file missing the 'linuxpath' key
    with tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8") as config_file:
        config_file.write("[DEFAULT]\nREREAD_ON_QUERY = True\n")
        config_file_path: str = config_file.name
    try:
        file_path, reread_on_query, ssl_enabled, certfile, keyfile = load_config(config_file_path)
        assert file_path is None
        assert not reread_on_query
        assert not ssl_enabled
        assert certfile is None
        assert keyfile is None
    finally:
        os.remove(config_file_path)


def test_config_file_does_not_exist() -> None:
    # Create a config file that references a non-existent search file.
    non_existent_search_file: str = "non_existent_search_file.txt"
    with tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8") as config_file:
        config_file.write(f"[DEFAULT]\nlinuxpath = {non_existent_search_file}\nREREAD_ON_QUERY = False\n")
        config_file_path: str = config_file.name
    try:
        file_path, reread_on_query, ssl_enabled, certfile, keyfile = load_config(config_file_path)
        assert file_path is None
        assert not reread_on_query
        assert not ssl_enabled
        assert certfile is None
        assert keyfile is None
    finally:
        os.remove(config_file_path)


def test_load_config_valid(tmp_path: Path) -> None:
    # Create a valid search file and configuration file using tmp_path
    search_file = tmp_path / "search.txt"
    search_file.write_text("line1\nline2\n")
    config_file = tmp_path / "config.ini"
    config_file.write_text(f"""
[DEFAULT]
linuxpath = {search_file}
REREAD_ON_QUERY = True
SSL_ENABLED = False
CERTFILE =
KEYFILE =
""")
    file_path, reread_on_query, ssl_enabled, certfile, keyfile = load_config(str(config_file))
    assert file_path == str(search_file)
    assert reread_on_query is True
    assert ssl_enabled is False
    assert certfile == ""
    assert keyfile == ""


###############################################################################
# Tests for search_string_in_file() and search_string_in_file_cached()
###############################################################################

def test_empty_query(tmp_path: Path) -> None:
    search_file = tmp_path / "file.txt"
    search_file.write_text("some content\n")
    result: str = search_string_in_file(str(search_file), "", True)
    assert result == "ERROR: EMPTY QUERY"


def test_file_not_found() -> None:
    result: str = search_string_in_file("nonexistent_file.txt", "query", True)
    assert result == "ERROR: FILE NOT FOUND"


def test_string_exists_reread(tmp_path: Path) -> None:
    search_file = tmp_path / "file.txt"
    search_file.write_text("match_line\nother_line\n")
    result: str = search_string_in_file(str(search_file), "match_line", True)
    assert result == "STRING EXISTS"


def test_string_not_found_reread(tmp_path: Path) -> None:
    search_file = tmp_path / "file.txt"
    search_file.write_text("line1\nline2\n")
    result: str = search_string_in_file(str(search_file), "nonexistent", True)
    assert result == "STRING NOT FOUND"


def test_string_exists_cached(tmp_path: Path) -> None:
    search_file = tmp_path / "file.txt"
    search_file.write_text("cached_line\nanother_line\n")
    # Ensure cache is cleared
    if hasattr(search_string_in_file_cached, "cached_lines"):
        del search_string_in_file_cached.cached_lines
    result: str = search_string_in_file_cached(str(search_file), "cached_line")
    assert result == "STRING EXISTS"


def test_string_not_found_cached(tmp_path: Path) -> None:
    search_file = tmp_path / "file.txt"
    search_file.write_text("line1\nline2\n")
    if hasattr(search_string_in_file_cached, "cached_lines"):
        del search_string_in_file_cached.cached_lines
    result: str = search_string_in_file_cached(str(search_file), "nonexistent")
    assert result == "STRING NOT FOUND"


def test_cached_read_error() -> None:
    # Ensure cache is cleared so that the exception is triggered
    if hasattr(search_string_in_file_cached, "cached_lines"):
        del search_string_in_file_cached.cached_lines
    with patch("builtins.open", side_effect=Exception("Cache read error")):
        result: str = search_string_in_file_cached("dummy_path", "query")
        assert "ERROR: Failed to read file: Cache read error" in result


###############################################################################
# Tests for log_search()
###############################################################################

def test_log_search_success(tmp_path: Path) -> None:
    # Use mock_open to verify log entry is written
    m = mock_open()
    with patch("builtins.open", m):
        log_search("test_query", "127.0.0.1:44445", 100.0, "STRING EXISTS")
    m.assert_called_with("server_log.txt", "a")
    handle = m()
    assert handle.write.called


def test_log_search_write_error() -> None:
    with patch("builtins.open", side_effect=Exception("Write failure")):
        with patch("builtins.print") as mock_print:
            log_search("test_query", "127.0.0.1:44445", 100.0, "STRING EXISTS")
            mock_print.assert_any_call("ERROR: Failed to write to log file: Write failure")


###############################################################################
# Tests for handle_client()
###############################################################################

@pytest.fixture
def search_file() -> Generator[str, None, None]:
    with tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8") as tmp_file:
        tmp_file.write("client_test_line")
        search_file_path: str = tmp_file.name
    yield search_file_path
    os.remove(search_file_path)


# Set up global variables in the server module before testing handle_client.
@pytest.fixture(autouse=True)
def setup_handle_client(search_file: str) -> None:
    import server
    server.path = search_file
    server.REREAD_ON_QUERY = True
    server.BUFFER_SIZE = 1024  # Ensure BUFFER_SIZE is defined


def test_handle_client_valid_query() -> None:
    fake_conn: MagicMock = MagicMock()
    fake_addr: str = "127.0.0.1"
    # Simulate a client that sends "client_test_line" then disconnects.
    fake_conn.recv.side_effect = [b"client_test_line", ConnectionResetError]
    with patch("server.log_search"):
        handle_client(fake_conn, fake_addr)
    calls = fake_conn.sendall.call_args_list
    # We expect the response "STRING EXISTS"
    assert any(b"STRING EXISTS" in call[0][0] for call in calls)


def test_handle_client_empty_query() -> None:
    fake_conn: MagicMock = MagicMock()
    fake_addr: str = "127.0.0.1"
    # Simulate a client that sends an empty query then disconnects.
    fake_conn.recv.side_effect = [b"", ConnectionResetError]
    with patch("server.log_search"):
        handle_client(fake_conn, fake_addr)
    calls = fake_conn.sendall.call_args_list
    assert any(b"ERROR: EMPTY QUERY" in call[0][0] for call in calls)


###############################################################################
# Tests for start_server()
###############################################################################

def test_start_server():
    with patch("server.socket.socket") as mock_socket:
        fake_socket = MagicMock()
        mock_socket.return_value = fake_socket
        with patch("server.ssl.create_default_context") as mock_ssl_context:
            fake_ssl_context = MagicMock()
            mock_ssl_context.return_value = fake_ssl_context
            # Override load_config to return dummy valid values.
            with patch("server.load_config", return_value=("/tmp/dummy.txt", True, False, "", "")):
                # Simulate one accept() call and then KeyboardInterrupt to exit the loop.
                fake_socket.accept.side_effect = [(MagicMock(), ("127.0.0.1", 12345)), KeyboardInterrupt]
                try:
                    start_server()
                except KeyboardInterrupt:
                    pass
    fake_socket.bind.assert_called_with(("0.0.0.0", 44445))


# Test for 200k.txt file existence and content, if such a file is expected.
class Test200kData:
    @pytest.fixture(autouse=True)
    def data_file(self, tmp_path: Path) -> Generator[str, None, None]:
        # Create a temporary 200k.txt file with some content.
        data_file = tmp_path / "200k.txt"
        data_file.write_text("data\n" * 10)
        yield str(data_file)
        # tmp_path fixture cleans up automatically.

    def test_file_exists(self, data_file: str) -> None:
        assert os.path.exists(data_file)

    def test_content_length(self, data_file: str) -> None:
        with open(data_file, "r") as f:
            content = f.read()
        assert len(content) > 0, "File content is empty!"


if __name__ == "__main__":
    pytest.main()
