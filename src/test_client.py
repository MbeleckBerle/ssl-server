import unittest
from unittest.mock import patch, MagicMock
import client  # Assuming your client code is in client.py

class TestClient(unittest.TestCase):
    @patch("client.socket.socket")
    @patch("builtins.input", side_effect=["exit"])  # Immediately exit
    def test_run_client_exit(self, mock_input, mock_socket_class):
        # Create a dummy socket instance.
        dummy_socket = MagicMock()
        # Simulate a greeting message from the server.
        dummy_socket.recv.return_value = b"Hello, you are connected to the server!\n"
        mock_socket_class.return_value = dummy_socket
        
        # Run the client; it should exit immediately.
        client.run_client("127.0.0.1", 44445)
        
        # Ensure the socket was connected and closed.
        dummy_socket.connect.assert_called_with(("127.0.0.1", 44445))
        dummy_socket.close.assert_called()

if __name__ == '__main__':
    unittest.main()
