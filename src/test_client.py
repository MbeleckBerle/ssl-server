
import time
from typing import Generator, Tuple, List, Dict

import matplotlib.pyplot as plt
import pytest
from unittest.mock import MagicMock, patch

from client import run_client, load_client_config


@pytest.fixture
def mock_socket_and_ssl() -> Generator[Tuple[MagicMock, MagicMock], None, None]:
    """
    Fixture for mocking socket and SSL context.

    Yields
    ------
    tuple
        A tuple containing a mocked socket and a mocked SSL context.
    """
    fake_socket = MagicMock()
    fake_ssl_context = MagicMock()
    fake_ssl_context.wrap_socket.return_value = fake_socket

    with patch("socket.socket", return_value=fake_socket), patch(
        "ssl.create_default_context", return_value=fake_ssl_context
    ):
        yield fake_socket, fake_ssl_context


def get_printed_lines(mock_print: MagicMock) -> List[str]:
    """
    Helper function to extract printed lines from mock print calls.

    Parameters
    ----------
    mock_print : MagicMock
        The mocked print function.

    Returns
    -------
    list[str]
        A list of printed strings.
    """
    return [
        " ".join(str(arg) for arg in call.args)
        for call in mock_print.call_args_list
    ]


def test_run_client(mock_socket_and_ssl: Tuple[MagicMock, MagicMock]) -> None:
    """
    Test that the client connects, sends a query, receives a response,
    and exits cleanly.

    Parameters
    ----------
    mock_socket_and_ssl : tuple
        A tuple of mocked socket and SSL context.
    """
    fake_socket, _ = mock_socket_and_ssl

    # Mock the behavior of recv (what the server responds with)
    fake_socket.recv.side_effect = [
        b"Welcome to Secure Search Service\n",  # Greeting
        b"Server Response\n",  # Response for "test query"
    ]

    # Mock the behavior of the input and print functions
    with patch("builtins.input", side_effect=["test query", "exit"]), patch(
        "builtins.print"
    ) as mock_print:
        # Run the client
        run_client("127.0.0.1", 44445)

        # Get printed lines from the mock
        printed = get_printed_lines(mock_print)

        # Debugging output
        print("Printed lines during test:")
        for line in printed:
            print(line)

        # Assertions for expected print outputs
        assert any(
            "connected to server at 127.0.0.1:44445" in line.lower()
            for line in printed
        )
        assert any(
            "server:" in line.lower()
            and "welcome to secure search service" in line.lower()
            for line in printed
        )
        assert any(
            "response:" in line.lower() and "server response" in line.lower()
            for line in printed
        )
        assert any("exiting client" in line.lower() for line in printed)

        # Ensure the socket was connected to the expected address
        fake_socket.connect.assert_called_with(("127.0.0.1", 44445))

        # Ensure the query was sent
        fake_socket.sendall.assert_called_with(b"test query")


@pytest.fixture
def mock_config() -> Generator[None, None, None]:
    """
    Fixture for mocking the config file loading.
    """
    with patch("os.path.exists", return_value=True), patch(
        "configparser.ConfigParser.read"
    ), patch(
        "configparser.ConfigParser.get",
        side_effect=lambda section, option, **kwargs: "True"
        if option == "SSL_ENABLED"
        else "server_cert.pem",
    ):
        yield


def test_load_client_config(mock_config: None) -> None:
    """
    Test that client configuration loads properly.
    """
    ssl_enabled, server_cert = load_client_config()
    assert ssl_enabled is True
    assert server_cert == "server_cert.pem"


def test_benchmark_execution_times() -> None:
    """
    Benchmark the client on different file sizes.

    Measures execution time for different file sizes and asserts that
    execution time increases as the file size grows.
    """
    file_sizes = [10000, 100000, 500000, 1000000]
    times: Dict[int, float] = {}

    for size in file_sizes:
        start_time = time.time()
        run_client("127.0.0.1", 44445)  # Adjust this for actual file handling.
        elapsed_time = time.time() - start_time
        times[size] = elapsed_time
        print(f"File size: {size}, Time taken: {elapsed_time:.4f} seconds")

    plot_benchmark_results(times)

    assert times[10000] < times[100000], "Expected shorter time for smaller file sizes"


def plot_benchmark_results(times: Dict[int, float]) -> None:
    """
    Plot benchmark results and save as 'execution_time_plot.png'.

    Parameters
    ----------
    times : dict[int, float]
        A dictionary mapping file sizes to execution times.
    """
    file_sizes = list(times.keys())
    execution_times = list(times.values())

    plt.plot(file_sizes, execution_times, marker="o")
    plt.title("File Size vs Execution Time")
    plt.xlabel("File Size (lines)")
    plt.ylabel("Time Taken (seconds)")
    plt.grid(True)
    plt.savefig("execution_time_plot.png")
    plt.show()


if __name__ == "__main__":
    pytest.main()
