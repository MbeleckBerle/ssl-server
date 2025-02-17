# import unittest
# from unittest.mock import patch, MagicMock
# import client  # Assuming your client code is in client.py

# class TestClient(unittest.TestCase):
#     @patch("client.socket.socket")
#     @patch("builtins.input", side_effect=["exit"])  # Immediately exit
#     def test_run_client_exit(self, mock_input, mock_socket_class):
#         # Create a dummy socket instance.
#         dummy_socket = MagicMock()
#         # Simulate a greeting message from the server.
#         dummy_socket.recv.return_value = b"Hello, you are connected to the server!\n"
#         mock_socket_class.return_value = dummy_socket
        
#         # Run the client; it should exit immediately.
#         client.run_client("127.0.0.1", 44445)
        
#         # Ensure the socket was connected and closed.
#         dummy_socket.connect.assert_called_with(("127.0.0.1", 44445))
#         dummy_socket.close.assert_called()

# if __name__ == '__main__':
#     unittest.main()









# import unittest
# from unittest.mock import patch, MagicMock
# import client  # Assuming your client code is in client.py

# class TestClient(unittest.TestCase):
    
#     @patch("socket.socket")  # Patch socket directly
#     @patch("builtins.input", side_effect=["exit"])  # Immediately exit
#     def test_run_client_exit(self, mock_input, mock_socket_class):
#         """
#         Test client exits immediately when 'exit' is entered.
#         """
#         dummy_socket = MagicMock()
#         dummy_socket.recv.return_value = b"Hello, you are connected to the server!\n"
#         mock_socket_class.return_value = dummy_socket
        
#         client.run_client("127.0.0.1", 44446)
        
#         # Ensure the socket was connected and closed.
#         dummy_socket.connect.assert_called_with(("127.0.0.1", 44446))
#         dummy_socket.close.assert_called()

#     @patch("socket.socket")  # Patch socket directly
#     @patch("builtins.input", side_effect=["", "exit"])  # Empty query then exit
#     def test_run_client_empty_query(self, mock_input, mock_socket_class):
#         """
#         Test client handles empty query input gracefully.
#         """
#         dummy_socket = MagicMock()
#         dummy_socket.recv.return_value = b"Hello, you are connected to the server!\n"
#         mock_socket_class.return_value = dummy_socket
        
#         client.run_client("127.0.0.1", 44446)
        
#         dummy_socket.connect.assert_called_with(("127.0.0.1", 44446))
#         dummy_socket.close.assert_called()

#     @patch("socket.socket")  # Patch socket directly
#     @patch("builtins.input", side_effect=["query", "exit"])
#     def test_run_client_valid_query(self, mock_input, mock_socket_class):
#         """
#         Test client successfully sends a valid query and receives a response.
#         """
#         dummy_socket = MagicMock()
#         dummy_socket.recv.side_effect = [b"Hello, you are connected to the server!\n", b"Server response\n"]
#         mock_socket_class.return_value = dummy_socket
        
#         client.run_client("127.0.0.1", 44446)
        
#         dummy_socket.connect.assert_called_with(("127.0.0.1", 44446))
#         dummy_socket.sendall.assert_called_with(b"query")
#         dummy_socket.close.assert_called()

# if __name__ == "__main__":
#     unittest.main()














import unittest
from unittest.mock import patch, MagicMock
import socket
import ssl
import configparser
from client import run_client, load_client_config

def get_printed_lines(mock_print):
    """
    Helper function: for each print call, join its arguments into a single string.
    Returns a list of strings.
    """
    return [" ".join(str(arg) for arg in call.args) for call in mock_print.call_args_list]

class TestClient(unittest.TestCase):

    @patch('builtins.input', side_effect=['test query', 'exit'])
    @patch('socket.socket')
    @patch('ssl.create_default_context')
    def test_run_client(self, mock_ssl_context, mock_socket, mock_input):
        """
        Test that the client connects, sends a query, receives a response, and exits cleanly.
        """
        # Set up a fake socket.
        fake_socket = MagicMock()
        mock_socket.return_value = fake_socket

        # Set up a fake SSL context.
        fake_ssl_context = MagicMock()
        mock_ssl_context.return_value = fake_ssl_context
        fake_ssl_context.wrap_socket.return_value = fake_socket

        # Simulate server responses:
        # First recv() returns the greeting; second returns the query response.
        fake_socket.recv.side_effect = [
            b"Welcome to Secure Search Service\n",  # Greeting
            b"Server Response\n"                      # Response for "test query"
        ]

        with patch("builtins.print") as mock_print:
            run_client("127.0.0.1", 44446)
            printed = get_printed_lines(mock_print)

            # Check for expected printed messages (case-insensitive search).
            self.assertTrue(
                any("connected to server at 127.0.0.1:44446" in line.lower() for line in printed),
                "Connected message not printed"
            )
            self.assertTrue(
                any("server:" in line.lower() and "welcome to secure search service" in line.lower() for line in printed),
                "Greeting message not printed"
            )
            self.assertTrue(
                any("response:" in line.lower() and "server response" in line.lower() for line in printed),
                "Response message not printed"
            )
            self.assertTrue(
                any("exiting client" in line.lower() for line in printed),
                "Exit message not printed"
            )

            # Verify that the connection and query sending occurred.
            fake_socket.connect.assert_called_with(("127.0.0.1", 44446))
            fake_socket.sendall.assert_called_with(b"test query")

    @patch("os.path.exists", return_value=True)
    @patch("configparser.ConfigParser.read")
    @patch("configparser.ConfigParser.get",
           side_effect=lambda section, option, **kwargs: "True" if option == "SSL_ENABLED" else "server_cert.pem")
    def test_load_client_config(self, mock_get, mock_read, mock_exists):
        """
        Test that client configuration loads properly.
        """
        ssl_enabled, server_cert = load_client_config()
        self.assertTrue(ssl_enabled, "SSL should be enabled as per mocked config.")
        self.assertEqual(server_cert, "server_cert.pem", "Server certificate path incorrect.")

if __name__ == '__main__':
    unittest.main()












