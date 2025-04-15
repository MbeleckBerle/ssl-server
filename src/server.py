import configparser
import os
import socket
import ssl
import threading
import time
from typing import Optional, Tuple, List
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
import logging

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[logging.FileHandler("server_log.txt"), logging.StreamHandler()],
)

HOST: str = "0.0.0.0"
PORT: int = 44445
path: Optional[str] = None
REREAD_ON_QUERY: bool = False
SSL_ENABLED: bool = False
CERTFILE: Optional[str] = None
KEYFILE: Optional[str] = None

# buffer overload mitigation
BUFFER_SIZE: int = 1024
MAX_QUERY_LENGTH: int = 1024  # limit query length to prevent buffer overload.
RATE_LIMIT: int = 5  # Max requests per 10 seconds
RATE_WINDOW: int = 10  # Time window in seconds
QUERY_TIMEOUT: int = 40/1000  # max time in execution time in ms

# Additional security constants:
SOCKET_TIMEOUT = 60  # seconds timeout for client connections
MAX_INCOMING_LENGTH = 2048  # Maximum allowed length of received raw data

client_requests = defaultdict(deque)
rate_limit_lock = threading.Lock()  # Ensure thread safety for rate limiting
cached_lines = None  # Cache for file content


def load_config(
    config_path: str = "config.ini",
) -> Tuple[Optional[str], bool, bool, Optional[str], Optional[str]]:
    if not os.path.exists(config_path):
        logging.error(
            f"Configuration file '{config_path}' not found. Please create it."
        )
        return None, False, False, None, None

    try:
        config = configparser.ConfigParser()
        config.read(config_path)

        path = config["DEFAULT"].get("linuxpath", "").strip()
        reread_on_query = (
            config["DEFAULT"].get(
                "REREAD_ON_QUERY", "False").strip().lower() == "true"
        )
        ssl_enabled = (
            config["DEFAULT"].get(
                "SSL_ENABLED", "False").strip().lower() == "true"
        )
        certfile = config["DEFAULT"].get("CERTFILE", "").strip()
        keyfile = config["DEFAULT"].get("KEYFILE", "").strip()

        if not os.path.exists(path):
            logging.error(
                f"Configured file '{path}' does not exist. \
                         Check 'linuxpath' in {config_path}."
            )
            return None, False, False, None, None

        if ssl_enabled and (
            not os.path.exists(certfile) or not os.path.exists(keyfile)
        ):
            logging.error(
                "SSL is enabled but certificate \
                                    or key does not exist."
            )
            return None, False, False, None, None

        return path, reread_on_query, ssl_enabled, certfile, keyfile

    except Exception as e:
        logging.error(f"Exception in load_config: {str(e)}")
        return None, False, False, None, None


def preprocess_file(path: str) -> Optional[List[Tuple[int, str]]]:
    try:
        lines_with_numbers: List[Tuple[int, str]] = []  # Initialize list
        with open(path, "r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, 1):  # Enumerate lines
                lines_with_numbers.append((line_number, line.strip()))
        return lines_with_numbers  # Return list of tuples
    except FileNotFoundError:
        logging.error(f"File not found: {path}")
        return None
    except PermissionError:
        logging.error(f"Permission denied: {path}")
        return None
    except Exception as e:
        logging.error(f"Failed to read file: {str(e)}")
    except UnicodeDecodeError:
        logging.error(
            f"File {path} contains invalid encoding. \
                             Unable to read."
        )
    return None


def sanitize_query(query: str) -> str:
    return " ".join(query.split())  # Normalize spaces


def search_string_in_file(path: str, query: str) -> str:
    """
    Searches for a query string in the specified file
    with a time constraint and returns line number.

    Args:
        path (str): The path to the file.
        query (str): The search query.

    Returns:
        str: "STRING EXISTS, LINE {line_number}" if found,\
            "STRING NOT FOUND" otherwise,
             or "ERROR: TIMEOUT" if execution exceeds the limit.
    """
    if len(query) > MAX_QUERY_LENGTH:
        return "ERROR: QUERY TOO LONG"

    if not query.strip():
        return "ERROR: EMPTY QUERY"

    query: str = sanitize_query(query)  # Normalize spaces

    if not os.path.exists(path):
        return "ERROR: FILE NOT FOUND"

    global cached_lines
    lines_with_numbers: Optional[List[Tuple[int, str]]]

    if REREAD_ON_QUERY:
        lines_with_numbers = preprocess_file(path)  # Reload file content
    else:
        if cached_lines is None:
            cached_lines = preprocess_file(path)  # Cache once if not loaded
        lines_with_numbers = cached_lines  # Assign cached lines
    if lines_with_numbers is None:
        return "ERROR: Failed to load file for searching."

    result: List[str] = ["ERROR: TIMEOUT"]  # Default response for timeout
    line_number_found: List[Optional[int]] = [None]  # Store the line number

    def perform_search() -> None:
        for line_number, line in lines_with_numbers:  # Iterate through lines
            if query in line:
                result[0] = f"STRING EXISTS, LINE {line_number}"  # show line
                line_number_found[0] = line_number  # Store line number
                return  # Stop at the first occurrence
        result[0] = "STRING NOT FOUND"  # String not found

    # Start the search in a separate thread with a timeout
    search_thread: threading.Thread = threading.Thread(target=perform_search)
    search_thread.start()
    search_thread.join(timeout=QUERY_TIMEOUT)

    if search_thread.is_alive():
        return "ERROR: TIMEOUT"

    return result[0]


def log_search(query: str, addr: str, exe_time: float, response: str) -> None:
    exe_response = f"Execution Time: {exe_time}ms, Result: {response}"
    log_entry = f"Query: '{query}', IP: {addr}, {exe_response}"
    logging.info(log_entry)


def rate_limit_exceeded(addr: str) -> bool:
    now = time.time()
    with rate_limit_lock:
        requests = client_requests[addr]
        # Remove requests that are outside the rate window
        while requests and requests[0] < now - RATE_WINDOW:
            requests.popleft()
        if len(requests) >= RATE_LIMIT:
            return True
        requests.append(now)
    return False


def handle_client(conn: socket.socket, addr: Tuple[str, int]) -> None:
    logging.info(f"New connection from {addr}")
    # Set timeout to protect against hanging connections
    conn.settimeout(SOCKET_TIMEOUT)
    conn.sendall(b"Hello, you are connected to the server!\n")

    try:
        while True:
            received_raw = conn.recv(BUFFER_SIZE)
            # Check for excessive incoming data length for extra protection.
            if len(received_raw) > MAX_INCOMING_LENGTH:
                conn.sendall(b"ERROR: Input data too large.\n")
                break

            if not received_raw:
                break

            try:
                received_data = received_raw.decode("utf-8")
            except UnicodeDecodeError:
                conn.sendall(b"ERROR: Unable to decode input.\n")
                break

            if received_data.strip() == "":
                response = "ERROR: EMPTY QUERY"
                conn.sendall(f"{response}\n".encode("utf-8"))
                continue

            if received_data.lower().strip() in {"exit", "quit"}:
                conn.sendall(b"Goodbye!\n")
                break

            if rate_limit_exceeded(addr[0]):
                response = "ERROR: RATE LIMIT EXCEEDED"
            else:
                start_time = time.time()
                response = search_string_in_file(path, received_data.strip())
                exe_time = round((time.time() - start_time) * 1000, 3)
                log_search(
                    received_data.strip(), f"{addr[0]}:{addr[1]}",
                    exe_time, response
                )

            conn.sendall(f"{response}\n".encode("utf-8"))
    except ConnectionResetError:
        logging.warning(f"Client {addr} disconnected unexpectedly.")
    except Exception as e:
        logging.error(f"Unexpected error with client {addr}: {str(e)}")

    except socket.timeout:
        logging.warning(f"Timeout: Client {addr} took too long to respond.")
        conn.sendall(b"ERROR: Connection timeout.\n")
    except UnicodeDecodeError:
        logging.warning(f"Decoding error from {addr}.")
        conn.sendall(b"ERROR: Unable to decode input.\n")

    finally:
        conn.close()


def start_server() -> None:
    global path, REREAD_ON_QUERY, SSL_ENABLED, CERTFILE, KEYFILE, cached_lines
    path, REREAD_ON_QUERY, SSL_ENABLED, CERTFILE, KEYFILE = load_config()

    if path is None:
        logging.error("Invalid configuration. Server cannot start.")
        return

    if not REREAD_ON_QUERY:
        cached_lines = preprocess_file(path)

    try:
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((HOST, PORT))
        server_sock.listen()
        print(f"Server is listening on {HOST}:{PORT}...")

        ssl_context = None
        if SSL_ENABLED:
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(certfile=CERTFILE, keyfile=KEYFILE)
            ssl_context.set_ciphers("ECDHE-RSA-AES128-GCM-SHA256")
            ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
            print("SSL is enabled for the server.")

        # Use ThreadPoolExecutor to handle multiple clients concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            while True:
                conn, addr = server_sock.accept()

                if SSL_ENABLED and ssl_context:
                    try:
                        conn = ssl_context.wrap_socket(conn, server_side=True)
                    except ssl.SSLError as e:
                        print(f"SSL error with client {addr}: {e}")
                        conn.close()
                        continue

                executor.submit(handle_client, conn, addr)

    except OSError as e:
        logging.error(f"ERROR: Failed to start server. Possible cause: {e}")
    except KeyboardInterrupt:
        logging.info("\nServer shutting down gracefully...")
    finally:
        server_sock.close()


if __name__ == "__main__":
    start_server()
