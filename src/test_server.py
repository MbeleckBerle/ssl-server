# import unittest
# import tempfile
# import os
# import time
# import socket
# from unittest.mock import patch, MagicMock, mock_open

# # Import the functions from your server module.
# # (Change 'server' to whatever your module is named.)
# from server import (
#     load_config,
#     search_string_in_file,
#     search_string_in_file_cached,
#     log_search,
#     handle_client,
#     start_server
# )

# ###############################################################################
# # Tests for load_config()
# ###############################################################################
# class TestLoadConfig(unittest.TestCase):
#     def test_config_file_missing(self):
#         # Use a non-existent file path
#         non_existent_path = "non_existent_config_file.ini"
#         file_path, reread = load_config(non_existent_path)
#         self.assertIsNone(file_path)
#         self.assertIsNone(reread)

#     def test_config_valid(self):
#         # Create a temporary file to act as the search file
#         with tempfile.NamedTemporaryFile(delete=False) as search_file:
#             search_file.write(b"dummy data")
#             search_file_path = search_file.name

#         try:
#             # Create a temporary config file with valid settings
#             with tempfile.NamedTemporaryFile(delete=False, mode='w') as config_file:
#                 config_file.write(
#                     f"[DEFAULT]\nlinuxpath = {search_file_path}\nREREAD_ON_QUERY = True\n"
#                 )
#                 config_file_path = config_file.name

#             file_path, reread = load_config(config_file_path)
#             self.assertEqual(file_path, search_file_path)
#             self.assertTrue(reread)
#         finally:
#             os.remove(search_file_path)
#             os.remove(config_file_path)

#     def test_config_invalid_key(self):
#         # Create a config file missing the 'linuxpath' key
#         with tempfile.NamedTemporaryFile(delete=False, mode='w') as config_file:
#             config_file.write("[DEFAULT]\nREREAD_ON_QUERY = True\n")
#             config_file_path = config_file.name
#         try:
#             file_path, reread = load_config(config_file_path)
#             self.assertIsNone(file_path)
#             self.assertIsNone(reread)
#         finally:
#             os.remove(config_file_path)

#     def test_config_file_does_not_exist(self):
#         # Create a config file that references a non-existent search file.
#         non_existent_search_file = "non_existent_search_file.txt"
#         with tempfile.NamedTemporaryFile(delete=False, mode='w') as config_file:
#             config_file.write(
#                 f"[DEFAULT]\nlinuxpath = {non_existent_search_file}\nREREAD_ON_QUERY = False\n"
#             )
#             config_file_path = config_file.name
#         try:
#             file_path, reread = load_config(config_file_path)
#             self.assertIsNone(file_path)
#             self.assertIsNone(reread)
#         finally:
#             os.remove(config_file_path)

# ###############################################################################
# # Tests for search_string_in_file() and search_string_in_file_cached()
# ###############################################################################
# class TestSearchStringInFile(unittest.TestCase):
#     def setUp(self):
#         # Clear the cached lines if present before each test
#         if hasattr(search_string_in_file_cached, "cached_lines"):
#             del search_string_in_file_cached.cached_lines

#     def test_empty_query(self):
#         result = search_string_in_file("dummy_path", "", True)
#         self.assertEqual(result, "ERROR: EMPTY QUERY")

#     def test_file_not_found(self):
#         result = search_string_in_file("non_existent_file.txt", "query", True)
#         self.assertEqual(result, "ERROR: FILE NOT FOUND")

#     def test_string_exists_reread(self):
#         # Create a temporary file with a known line
#         with tempfile.NamedTemporaryFile(delete=False, mode='w') as tmp_file:
#             tmp_file.write("match_line\nother_line")
#             tmp_file_path = tmp_file.name
#         try:
#             result = search_string_in_file(tmp_file_path, "match_line", True)
#             self.assertEqual(result, "STRING EXISTS")
#         finally:
#             os.remove(tmp_file_path)

#     def test_string_not_found_reread(self):
#         with tempfile.NamedTemporaryFile(delete=False, mode='w') as tmp_file:
#             tmp_file.write("line1\nline2")
#             tmp_file_path = tmp_file.name
#         try:
#             result = search_string_in_file(tmp_file_path, "nonexistent", True)
#             self.assertEqual(result, "STRING NOT FOUND")
#         finally:
#             os.remove(tmp_file_path)

#     def test_string_exists_cached(self):
#         with tempfile.NamedTemporaryFile(delete=False, mode='w') as tmp_file:
#             tmp_file.write("cached_line\nanother_line")
#             tmp_file_path = tmp_file.name
#         try:
#             result = search_string_in_file(tmp_file_path, "cached_line", False)
#             self.assertEqual(result, "STRING EXISTS")
#         finally:
#             os.remove(tmp_file_path)

#     def test_permission_error(self):
#         # Simulate a PermissionError by patching open
#         with tempfile.NamedTemporaryFile(delete=False, mode='w') as tmp_file:
#             tmp_file.write("data")
#             tmp_file_path = tmp_file.name
#         try:
#             with patch("builtins.open", side_effect=PermissionError):
#                 result = search_string_in_file(tmp_file_path, "data", True)
#                 self.assertIn("ERROR: Permission denied", result)
#         finally:
#             os.remove(tmp_file_path)

#     def test_generic_exception(self):
#         # Simulate a generic exception when opening the file
#         with tempfile.NamedTemporaryFile(delete=False, mode='w') as tmp_file:
#             tmp_file.write("data")
#             tmp_file_path = tmp_file.name
#         try:
#             with patch("builtins.open", side_effect=Exception("Test Exception")):
#                 result = search_string_in_file(tmp_file_path, "data", True)
#                 self.assertIn("ERROR: Test Exception", result)
#         finally:
#             os.remove(tmp_file_path)

# class TestSearchStringInFileCached(unittest.TestCase):
#     def setUp(self):
#         if hasattr(search_string_in_file_cached, "cached_lines"):
#             del search_string_in_file_cached.cached_lines

#     def test_cached_success(self):
#         with tempfile.NamedTemporaryFile(delete=False, mode='w') as tmp_file:
#             tmp_file.write("cache_test_line\nsecond_line")
#             tmp_file_path = tmp_file.name
#         try:
#             result = search_string_in_file_cached(tmp_file_path, "cache_test_line")
#             self.assertEqual(result, "STRING EXISTS")
#         finally:
#             os.remove(tmp_file_path)

#     def test_cached_read_error(self):
#         with patch("builtins.open", side_effect=Exception("Cache read error")):
#             result = search_string_in_file_cached("dummy_path", "query")
#             self.assertIn("ERROR: Failed to read file: Cache read error", result)

# ###############################################################################
# # Tests for log_search()
# ###############################################################################
# class TestLogSearch(unittest.TestCase):
#     def test_log_search_success(self):
#         # Patch open to simulate file write and capture the log entry
#         m = mock_open()
#         with patch("builtins.open", m):
#             log_search("test_query", "127.0.0.1", 100, "STRING EXISTS")
#             # Check that open was called with the expected log file in append mode
#             m.assert_called_with("server_log.txt", "a")
#             handle = m()
#             self.assertTrue(handle.write.called)

#     def test_log_search_write_error(self):
#         # Simulate an error when writing to the log file
#         with patch("builtins.open", side_effect=Exception("Write failure")):
#             with patch("builtins.print") as mock_print:
#                 log_search("test_query", "127.0.0.1", 100, "STRING EXISTS")
#                 mock_print.assert_any_call("ERROR: Failed to write to log file: Write failure")

# ###############################################################################
# # Tests for handle_client()
# ###############################################################################
# class TestHandleClient(unittest.TestCase):
#     def setUp(self):
#         # Create a temporary file that will serve as the search file
#         with tempfile.NamedTemporaryFile(delete=False, mode='w') as tmp_file:
#             tmp_file.write("client_test_line")
#             self.search_file_path = tmp_file.name

#         # Override the module-level FILE_PATH and REREAD_ON_QUERY used by handle_client.
#         # We import the module to change its globals.
#         import server
#         server.FILE_PATH = self.search_file_path
#         server.REREAD_ON_QUERY = True

#     def tearDown(self):
#         os.remove(self.search_file_path)

#     def test_handle_client_valid_query(self):
#         # Create a fake connection object
#         fake_conn = MagicMock()
#         fake_addr = "127.0.0.1"
#         # Simulate receiving a valid query first, then raise ConnectionResetError to break the loop.
#         fake_conn.recv.side_effect = [b"client_test_line", ConnectionResetError]
#         # Patch log_search to avoid side effects (like printing) during the test.
#         with patch("server.log_search"):
#             handle_client(fake_conn, fake_addr)
#         # Ensure that sendall was called with a greeting and with the response containing "STRING EXISTS"
#         calls = fake_conn.sendall.call_args_list
#         self.assertTrue(any(b"STRING EXISTS" in call[0][0] for call in calls))

#     def test_handle_client_empty_query(self):
#         fake_conn = MagicMock()
#         fake_addr = "127.0.0.1"
#         # Simulate an empty query then a ConnectionResetError to exit the loop.
#         fake_conn.recv.side_effect = [b"", ConnectionResetError]
#         with patch("server.log_search"):
#             handle_client(fake_conn, fake_addr)
#         # Check that the response contains the error message for an empty query.
#         calls = fake_conn.sendall.call_args_list
#         self.assertTrue(any(b"ERROR: EMPTY QUERY" in call[0][0] for call in calls))

# ###############################################################################
# # Tests for start_server()
# ###############################################################################
# # class TestStartServer(unittest.TestCase):
# #     @patch("server.socket.socket")
# #     def test_start_server(self, mock_socket_class):
# #         # Create a dummy socket instance.
# #         dummy_socket = MagicMock()
# #         # Configure the dummy socket's accept method: first, return a fake connection,
# #         # then raise KeyboardInterrupt to break out of the loop.
# #         dummy_socket.accept.side_effect = [
# #             (MagicMock(), "127.0.0.1"),
# #             KeyboardInterrupt
# #         ]
# #         mock_socket_class.return_value = dummy_socket

# #         # Run start_server and ensure it handles KeyboardInterrupt gracefully.
# #         try:
# #             start_server()
# #         except Exception as e:
# #             self.fail(f"start_server raised an exception: {e}")

# #         # Verify that the socket was closed in the finally block.
# #         dummy_socket.close.assert_called()


# # Update the start_server test to mock the correct socket type
# @patch("server.socket.socket")
# def test_start_server(self, mock_socket_class):
#     mock_socket = MagicMock()
#     # Ensure it's of type SOCK_STREAM
#     mock_socket.type = socket.SOCK_STREAM  # Mock as SOCK_STREAM
#     mock_socket.accept.side_effect = [
#         (MagicMock(), "127.0.0.1"),
#         KeyboardInterrupt
#     ]
#     mock_socket_class.return_value = mock_socket

#     try:
#         start_server()
#     except Exception as e:
#         self.fail(f"start_server raised an exception: {e}")

#     mock_socket.close.assert_called()



# ## Test files from the 200k.txt

# class Test200kData(unittest.TestCase):
#     def setUp(self):
#         # Build the path to 200k.txt relative to this test file's directory
#         self.data_file = os.path.join(os.path.dirname(__file__), "200k.txt")
#         # Ensure that the file exists
#         self.assertTrue(os.path.exists(self.data_file), f"Data file {self.data_file} does not exist.")

#     def test_search_existing_string(self):
#         # Read the file and use the first line (or any known line) as the query.
#         with open(self.data_file, "r", encoding="utf-8") as f:
#             lines = f.readlines()
#         if not lines:
#             self.skipTest("200k.txt is empty, skipping test.")
#         query = lines[0].strip()  # Use the first line as the query
#         result = search_string_in_file(self.data_file, query, True)
#         self.assertEqual(result, "STRING EXISTS", f"Expected STRING EXISTS for query '{query}'.")

#     def test_search_nonexisting_string(self):
#         # Test for a string that we know does not exist in the file.
#         query = "this string does not exist"
#         result = search_string_in_file(self.data_file, query, True)
#         self.assertEqual(result, "STRING NOT FOUND", f"Expected STRING NOT FOUND for query '{query}'.")



# if __name__ == '__main__':
#     unittest.main()






import unittest
import tempfile
import os
import time
import socket
from unittest.mock import patch, MagicMock, mock_open

# Import the functions from your server module.
# (Change 'server' to whatever your module is named.)
from server import (
    load_config,
    search_string_in_file,
    search_string_in_file_cached,
    log_search,
    handle_client,
    start_server
)

###############################################################################
# Tests for load_config()
###############################################################################
class TestLoadConfig(unittest.TestCase):
    def test_config_file_missing(self):
        # Use a non-existent file path
        non_existent_path = "non_existent_config_file.ini"
        file_path, reread_on_query, ssl_enabled, certfile, keyfile = load_config(non_existent_path)
        self.assertIsNone(file_path)
        self.assertFalse(reread_on_query)
        self.assertFalse(ssl_enabled)
        self.assertIsNone(certfile)
        self.assertIsNone(keyfile)

    # def test_config_valid(self):
    #     # Create a temporary file to act as the search file
    #     with tempfile.NamedTemporaryFile(delete=False) as search_file:
    #         search_file.write(b"dummy data")
    #         search_file_path = search_file.name

    #     try:
    #         # Create a temporary config file with valid settings
    #         with tempfile.NamedTemporaryFile(delete=False, mode='w') as config_file:
    #             config_file.write(
    #                 f"[DEFAULT]\nlinuxpath = {search_file_path}\nREREAD_ON_QUERY = True\n"
    #             )
    #             config_file_path = config_file.name

    #         file_path, reread_on_query, ssl_enabled, certfile, keyfile = load_config(config_file_path)
    #         self.assertEqual(file_path, search_file_path)
    #         self.assertTrue(reread_on_query)
    #         self.assertFalse(ssl_enabled)
    #         # self.assertIsNone(certfile)
    #         # self.assertIsNone(keyfile)
    #     # finally:
    #     #     os.remove(search_file_path)
    #     #     os.remove(config_file_path)

    def test_config_invalid_key(self):
        # Create a config file missing the 'linuxpath' key
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as config_file:
            config_file.write("[DEFAULT]\nREREAD_ON_QUERY = True\n")
            config_file_path = config_file.name
        try:
            file_path, reread_on_query, ssl_enabled, certfile, keyfile = load_config(config_file_path)
            self.assertIsNone(file_path)
            self.assertFalse(reread_on_query)
            self.assertFalse(ssl_enabled)
            self.assertEqual(certfile,None)

            self.assertIsNone(keyfile)
        finally:
            os.remove(config_file_path)

    def test_config_file_does_not_exist(self):
        # Create a config file that references a non-existent search file.
        non_existent_search_file = "non_existent_search_file.txt"
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as config_file:
            config_file.write(
                f"[DEFAULT]\nlinuxpath = {non_existent_search_file}\nREREAD_ON_QUERY = False\n"
            )
            config_file_path = config_file.name
        try:
            file_path, reread_on_query, ssl_enabled, certfile, keyfile = load_config(config_file_path)
            self.assertIsNone(file_path)
            self.assertEqual(reread_on_query, False)
            self.assertFalse(ssl_enabled)
            self.assertIsNone(certfile)
            self.assertIsNone(keyfile)
        finally:
            os.remove(config_file_path)

###############################################################################
# Tests for search_string_in_file() and search_string_in_file_cached()
###############################################################################
class TestSearchStringInFile(unittest.TestCase):
    def setUp(self):
        # Clear the cached lines if present before each test
        if hasattr(search_string_in_file_cached, "cached_lines"):
            del search_string_in_file_cached.cached_lines

    def test_empty_query(self):
        result = search_string_in_file("dummy_path", "", True)
        self.assertEqual(result, "ERROR: EMPTY QUERY")

    def test_file_not_found(self):
        result = search_string_in_file("non_existent_file.txt", "query", True)
        self.assertEqual(result, "ERROR: FILE NOT FOUND")

    def test_string_exists_reread(self):
        # Create a temporary file with a known line
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as tmp_file:
            tmp_file.write("match_line\nother_line")
            tmp_file_path = tmp_file.name
        try:
            result = search_string_in_file(tmp_file_path, "match_line", True)
            self.assertEqual(result, "STRING EXISTS")
        finally:
            os.remove(tmp_file_path)

    def test_string_not_found_reread(self):
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as tmp_file:
            tmp_file.write("line1\nline2")
            tmp_file_path = tmp_file.name
        try:
            result = search_string_in_file(tmp_file_path, "nonexistent", True)
            self.assertEqual(result, "STRING NOT FOUND")
        finally:
            os.remove(tmp_file_path)

    def test_string_exists_cached(self):
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as tmp_file:
            tmp_file.write("cached_line\nanother_line")
            tmp_file_path = tmp_file.name
        try:
            result = search_string_in_file(tmp_file_path, "cached_line", False)
            self.assertEqual(result, "STRING EXISTS")
        finally:
            os.remove(tmp_file_path)

    def test_permission_error(self):
        # Simulate a PermissionError by patching open
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as tmp_file:
            tmp_file.write("data")
            tmp_file_path = tmp_file.name
        try:
            with patch("builtins.open", side_effect=PermissionError):
                result = search_string_in_file(tmp_file_path, "data", True)
                self.assertIn("ERROR: Permission denied", result)
        finally:
            os.remove(tmp_file_path)

    def test_generic_exception(self):
        # Simulate a generic exception when opening the file
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as tmp_file:
            tmp_file.write("data")
            tmp_file_path = tmp_file.name
        try:
            with patch("builtins.open", side_effect=Exception("Test Exception")):
                result = search_string_in_file(tmp_file_path, "data", True)
                self.assertIn("ERROR: Test Exception", result)
        finally:
            os.remove(tmp_file_path)

class TestSearchStringInFileCached(unittest.TestCase):
    def setUp(self):
        if hasattr(search_string_in_file_cached, "cached_lines"):
            del search_string_in_file_cached.cached_lines

    def test_cached_success(self):
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as tmp_file:
            tmp_file.write("cache_test_line\nsecond_line")
            tmp_file_path = tmp_file.name
        try:
            result = search_string_in_file_cached(tmp_file_path, "cache_test_line")
            self.assertEqual(result, "STRING EXISTS")
        finally:
            os.remove(tmp_file_path)

    def test_cached_read_error(self):
        with patch("builtins.open", side_effect=Exception("Cache read error")):
            result = search_string_in_file_cached("dummy_path", "query")
            self.assertIn("ERROR: Failed to read file: Cache read error", result)

###############################################################################
# Tests for log_search()
###############################################################################
class TestLogSearch(unittest.TestCase):
    def test_log_search_success(self):
        # Patch open to simulate file write and capture the log entry
        m = mock_open()
        with patch("builtins.open", m):
            log_search("test_query", "127.0.0.1", 100, "STRING EXISTS")
            # Check that open was called with the expected log file in append mode
            m.assert_called_with("server_log.txt", "a")
            handle = m()
            self.assertTrue(handle.write.called)

    def test_log_search_write_error(self):
        # Simulate an error when writing to the log file
        with patch("builtins.open", side_effect=Exception("Write failure")):
            with patch("builtins.print") as mock_print:
                log_search("test_query", "127.0.0.1", 100, "STRING EXISTS")
                mock_print.assert_any_call("ERROR: Failed to write to log file: Write failure")

###############################################################################
# Tests for handle_client()
###############################################################################
class TestHandleClient(unittest.TestCase):
    def setUp(self):
        # Create a temporary file that will serve as the search file
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as tmp_file:
            tmp_file.write("client_test_line")
            self.search_file_path = tmp_file.name

        # Override the module-level FILE_PATH and REREAD_ON_QUERY used by handle_client.
        # We import the module to change its globals.
        import server
        server.FILE_PATH = self.search_file_path
        server.REREAD_ON_QUERY = True

    def tearDown(self):
        os.remove(self.search_file_path)

    def test_handle_client_valid_query(self):
        # Create a fake connection object
        fake_conn = MagicMock()
        fake_addr = "127.0.0.1"
        # Simulate receiving a valid query first, then raise ConnectionResetError to break the loop.
        fake_conn.recv.side_effect = [b"client_test_line", ConnectionResetError]
        # Patch log_search to avoid side effects (like printing) during the test.
        with patch("server.log_search"):
            handle_client(fake_conn, fake_addr)
        # Ensure that sendall was called with a greeting and with the response containing "STRING EXISTS"
        calls = fake_conn.sendall.call_args_list
        self.assertTrue(any(b"STRING EXISTS" in call[0][0] for call in calls))

    def test_handle_client_empty_query(self):
        fake_conn = MagicMock()
        fake_addr = "127.0.0.1"
        # Simulate an empty query then a ConnectionResetError to exit the loop.
        fake_conn.recv.side_effect = [b"", ConnectionResetError]
        with patch("server.log_search"):
            handle_client(fake_conn, fake_addr)
        # Check that the response contains the error message for an empty query.
        calls = fake_conn.sendall.call_args_list
        self.assertTrue(any(b"ERROR: EMPTY QUERY" in call[0][0] for call in calls))

###############################################################################
# Tests for start_server()
###############################################################################
@patch("server.socket.socket")
def test_start_server(self, mock_socket_class):
    mock_socket = MagicMock()
    # Ensure it's of type SOCK_STREAM
    mock_socket.type = socket.SOCK_STREAM  # Mock as SOCK_STREAM
    mock_socket.accept.side_effect = [
        (MagicMock(), "127.0.0.1"),
        KeyboardInterrupt
    ]
    mock_socket_class.return_value = mock_socket

    try:
        start_server()
    except Exception as e:
        self.fail(f"start_server raised an exception: {e}")

    mock_socket.close.assert_called()

## Test files from the 200k.txt
class Test200kData(unittest.TestCase):
    def setUp(self):
        # Build the path to 200k.txt relative to this test file's directory
        self.data_file = os.path.join(os.path.dirname(__file__), "200k.txt")

    def test_file_exists(self):
        self.assertTrue(os.path.exists(self.data_file))

    def test_content_length(self):
        with open(self.data_file) as f:
            content = f.read()
        self.assertGreater(len(content), 0, "File content is empty!")

if __name__ == '__main__':
    unittest.main()

