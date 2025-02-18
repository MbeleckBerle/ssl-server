
import os
import socket
import tempfile
from typing import Generator, Tuple, Dict, List

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
    file_path, reread_on_query, ssl_enabled, certfile, keyfile = load_config(
        non_existent_path
    )
    assert file_path is None
    assert not reread_on_query
    assert not ssl_enabled
    assert certfile is None
    assert keyfile is None


def test_config_invalid_key() -> None:
    # Create a config file missing the 'linuxpath' key
    with tempfile.NamedTemporaryFile(delete=False, mode="w") as config_file:
        config_file.write("[DEFAULT]\nREREAD_ON_QUERY = True\n")
        config_file_path: str = config_file.name
    try:
        file_path, reread_on_query, ssl_enabled, certfile, keyfile = load_config(
            config_file_path
        )
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
    with tempfile.NamedTemporaryFile(delete=False, mode="w") as config_file:
        config_file.write(
            f"[DEFAULT]\nlinuxpath = {non_existent_search_file}\nREREAD_ON_QUERY = False\n"
        )
        config_file_path: str = config_file.name
    try:
        file_path, reread_on_query, ssl_enabled, certfile, keyfile = load_config(
            config_file_path
        )
        assert file_path is None
        assert not reread_on_query
        assert not ssl_enabled
        assert certfile is None
        assert keyfile is None
    finally:
        os.remove(config_file_path)


###############################################################################
# Tests for search_string_in_file() and search_string_in_file_cached()
###############################################################################


@pytest.fixture
def reset_cache() -> None:
    if hasattr(search_string_in_file_cached, "cached_lines"):
        del search_string_in_file_cached.cached_lines


def test_empty_query() -> None:
    result: str = search_string_in_file("dummy_path", "", True)
    assert result == "ERROR: EMPTY QUERY"


def test_file_not_found() -> None:
    result: str = search_string_in_file("non_existent_file.txt", "query", True)
    assert result == "ERROR: FILE NOT FOUND"


def test_string_exists_reread() -> None:
    with tempfile.NamedTemporaryFile(delete=False, mode="w") as tmp_file:
        tmp_file.write("match_line\nother_line")
        tmp_file_path: str = tmp_file.name
    try:
        result: str = search_string_in_file(tmp_file_path, "match_line", True)
        assert result == "STRING EXISTS"
    finally:
        os.remove(tmp_file_path)


def test_string_not_found_reread() -> None:
    with tempfile.NamedTemporaryFile(delete=False, mode="w") as tmp_file:
        tmp_file.write("line1\nline2")
        tmp_file_path: str = tmp_file.name
    try:
        result: str = search_string_in_file(tmp_file_path, "nonexistent", True)
        assert result == "STRING NOT FOUND"
    finally:
        os.remove(tmp_file_path)


def test_string_exists_cached(reset_cache) -> None:
    with tempfile.NamedTemporaryFile(delete=False, mode="w") as tmp_file:
        tmp_file.write("cached_line\nanother_line")
        tmp_file_path: str = tmp_file.name
    try:
        result: str = search_string_in_file_cached(tmp_file_path, "cached_line")
        assert result == "STRING EXISTS"
    finally:
        os.remove(tmp_file_path)


def test_permission_error() -> None:
    with tempfile.NamedTemporaryFile(delete=False, mode="w") as tmp_file:
        tmp_file.write("data")
        tmp_file_path: str = tmp_file.name
    try:
        with patch("builtins.open", side_effect=PermissionError):
            result: str = search_string_in_file(tmp_file_path, "data", True)
            assert "ERROR: Permission denied" in result
    finally:
        os.remove(tmp_file_path)


def test_generic_exception() -> None:
    with tempfile.NamedTemporaryFile(delete=False, mode="w") as tmp_file:
        tmp_file.write("data")
        tmp_file_path: str = tmp_file.name
    try:
        with patch("builtins.open", side_effect=Exception("Test Exception")):
            result: str = search_string_in_file(tmp_file_path, "data", True)
            assert "ERROR: Test Exception" in result
    finally:
        os.remove(tmp_file_path)


class TestSearchStringInFileCached:
    @pytest.fixture(autouse=True)
    def reset_cache(self) -> None:
        if hasattr(search_string_in_file_cached, "cached_lines"):
            del search_string_in_file_cached.cached_lines

    def test_cached_success(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False, mode="w") as tmp_file:
            tmp_file.write("cache_test_line\nsecond_line")
            tmp_file_path: str = tmp_file.name
        try:
            result: str = search_string_in_file_cached(tmp_file_path, "cache_test_line")
            assert result == "STRING EXISTS"
        finally:
            os.remove(tmp_file_path)

    def test_cached_read_error(self) -> None:
        with patch("builtins.open", side_effect=Exception("Cache read error")):
            result: str = search_string_in_file_cached("dummy_path", "query")
            assert "ERROR: Failed to read file: Cache read error" in result


###############################################################################
# Tests for log_search()
###############################################################################


def test_log_search_success() -> None:
    """
    Test that log_search writes to the server log file successfully.
    """
    m = mock_open()
    with patch("builtins.open", m):
        log_search("test_query", "127.0.0.1", 100, "STRING EXISTS")
        m.assert_called_with("server_log.txt", "a")
        handle = m()
        assert handle.write.called


def test_log_search_write_error() -> None:
    with patch("builtins.open", side_effect=Exception("Write failure")):
        with patch("builtins.print") as mock_print:
            log_search("test_query", "127.0.0.1", 100, "STRING EXISTS")
            mock_print.assert_any_call("ERROR: Failed to write to log file: Write failure")


###############################################################################
# Tests for handle_client()
###############################################################################


@pytest.fixture
def search_file() -> Generator[str, None, None]:
    with tempfile.NamedTemporaryFile(delete=False, mode="w") as tmp_file:
        tmp_file.write("client_test_line")
        search_file_path: str = tmp_file.name
    yield search_file_path
    os.remove(search_file_path)


@pytest.fixture(autouse=True)
def setup_handle_client(search_file: str) -> None:
    import server

    server.FILE_PATH = search_file
    server.REREAD_ON_QUERY = True


def test_handle_client_valid_query(search_file: str) -> None:
    fake_conn: MagicMock = MagicMock()
    fake_addr: str = "127.0.0.1"
    fake_conn.recv.side_effect = [b"client_test_line", ConnectionResetError]
    with patch("server.log_search"):
        handle_client(fake_conn, fake_addr)
    calls: List = fake_conn.sendall.call_args_list
    assert any(b"STRING EXISTS" in call[0][0] for call in calls)


def test_handle_client_empty_query(search_file: str) -> None:
    fake_conn: MagicMock = MagicMock()
    fake_addr: str = "127.0.0.1"
    fake_conn.recv.side_effect = [b"", ConnectionResetError]
    with patch("server.log_search"):
        handle_client(fake_conn, fake_addr)
    calls: List = fake_conn.sendall.call_args_list
    assert any(b"ERROR: EMPTY QUERY" in call[0][0] for call in calls)


###############################################################################
# Tests for start_server()
###############################################################################


class Test200kData:
    @pytest.fixture(autouse=True)
    def data_file(self) -> Generator[str, None, None]:
        data_file: str = os.path.join(os.path.dirname(__file__), "200k.txt")
        yield data_file
        assert os.path.exists(data_file)

    def test_file_exists(self, data_file: str) -> None:
        assert os.path.exists(data_file)

    def test_content_length(self, data_file: str) -> None:
        with open(data_file) as f:
            content: str = f.read()
        assert len(content) > 0, "File content is empty!"


if __name__ == "__main__":
    pytest.main()
