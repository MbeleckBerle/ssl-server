import socket
import ssl
import time
import matplotlib.pyplot as plt
from typing import Tuple, List, Optional

BUFFER_SIZE: int = 1024
SSL_ENABLED: bool = True
HOST: str = '127.0.0.1'
PORT: int = 44445
CERTFILE: str = './cert.pem'  # Update with your certificate path
KEYFILE: str = './key.pem'    # Update with your key path


def create_ssl_socket(host: str, port: int, certfile: str,
                      keyfile: str) -> ssl.SSLSocket:
    context: ssl.SSLContext = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_cert_chain(certfile=certfile, keyfile=keyfile)
    context.set_ciphers('ECDHE-RSA-AES128-GCM-SHA256')
    context.minimum_version = ssl.TLSVersion.TLSv1_2

    # Disable hostname verification (use only for testing!)
    context.check_hostname = False

    # Load the server's certificate as a trusted root
    context.load_verify_locations(certfile)

    conn: ssl.SSLSocket = context.wrap_socket(socket.socket(socket.AF_INET),
                                              server_hostname=host)
    conn.connect((host, port))
    return conn


def query_server(host: str, port: int,
                 query: str) -> Tuple[Optional[str], Optional[float]]:
    try:
        with create_ssl_socket(host, port, CERTFILE, KEYFILE) as conn:
            start_time: float = time.time()  # Start time
            conn.sendall(query.encode('utf-8'))
            response: bytes = conn.recv(BUFFER_SIZE)
            execution_time: float = round((time.time() - start_time) * 1000, 3)
            return response.decode('utf-8'), execution_time
    except socket.error as e:
        print(f"ERROR: Client error: {e}")
        return None, None


def test_with_file_sizes() -> Tuple[List[int], List[Optional[float]]]:
    file_sizes: List[int] = [
        10000, 20000, 50000, 100000, 200000, 500000, 750000, 1000000
    ]

    execute_times: List[Optional[float]] = []

    for size in file_sizes:
        print(f"Testing with file size: {size}")
        query: str = "test_string"
        response, exec_time = query_server(HOST, PORT, query)
        if response:
            print(f"Query '{query}' succeeded. Execution time: {exec_time} ms")
            execute_times.append(exec_time)
        else:
            print(f"Query '{query}' failed.")
            execute_times.append(None)

        time.sleep(1)  # Adding a delay between queries

    return file_sizes, execute_times


def plot_performance(file_sizes: List[int],
                     execute_times: List[Optional[float]]) -> None:
    plt.figure(figsize=(12, 6))  # Increase figure size for better readability

    # Use a smooth line with distinct markers
    plt.plot(file_sizes, execute_times, marker='o',
             linestyle='--', color='b', markersize=8,
             linewidth=2, label="Execution Time")

    # Labels and title
    plt.xlabel('File Size (bytes)', fontsize=14)
    plt.ylabel('Execution Time (ms)', fontsize=14)
    plt.title('Execution Time vs File Size', fontsize=16, fontweight='bold')

    # Grid and axis styling
    plt.grid(True, linestyle='--', linewidth=0.5, alpha=0.7)
    plt.yticks(fontsize=12)

    # Adding minor ticks for more vertical grid lines
    plt.minorticks_on()
    plt.grid(which='minor', linestyle=':', linewidth=0.5, alpha=0.5)

    # Annotate points with execution time values
    for i, txt in enumerate(execute_times):
        if txt is not None:
            plt.annotate(f"{txt} ms", (file_sizes[i], execute_times[i]),
                         textcoords="offset points", xytext=(0, 8),
                         ha='center', fontsize=10,
                         color='darkred')

    # Save and show the plot
    plt.savefig('performance_plot.png', dpi=300, bbox_inches='tight')
    plt.legend()
    plt.show()


if __name__ == "__main__":
    file_sizes, execute_times = test_with_file_sizes()
    plot_performance(file_sizes, execute_times)
