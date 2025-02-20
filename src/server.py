import configparser
import os
import socket
import ssl
import threading
import time
import sys
from datetime import datetime
from typing import Optional, Tuple
from collections import defaultdict

HOST: str = "0.0.0.0"
PORT: int = 44445
path: Optional[str] = None
REREAD_ON_QUERY: bool = False
SSL_ENABLED: bool = False
CERTFILE: Optional[str] = None
KEYFILE: Optional[str] = None
BUFFER_SIZE: int = 1024
cached_lines: Optional[set] = None
MAX_QUERY_LENGTH: int = 1024
RATE_LIMIT: int = 5  # Max requests per 10 seconds
RATE_WINDOW: int = 10  # Time window in seconds
client_requests = defaultdict(list)
rate_limit_lock = threading.Lock()  # Ensure thread safety for rate limiting


def load_config(config_path: str = "config.ini") -> Tuple[Optional[str], bool,
                                                          bool, Optional[str],
                                                          Optional[str]]:
    if not os.path.exists(config_path):
        print(f"ERROR: Configuration file '{config_path}'\
              not found. Please create it.")
        return None, False, False, None, None

    config = configparser.ConfigParser()
    config.read(config_path)

    try:
        path = config["DEFAULT"].get("linuxpath", "").strip()
        reread_on_query = config["DEFAULT"].get(
            "REREAD_ON_QUERY",
            "False").strip().lower() == "true"
        ssl_enabled = config["DEFAULT"].get("SSL_ENABLED",
                                            "False").strip().lower() == "true"
        certfile = config["DEFAULT"].get("CERTFILE", "").strip()
        keyfile = config["DEFAULT"].get("KEYFILE", "").strip()

        if not os.path.exists(path):
            print(f"ERROR: Configured file '{path}'\
                  does not exist. Check 'linuxpath' in {config_path}.")
            return None, False, False, None, None

        if ssl_enabled and (not os.path.exists(certfile) or not
                            os.path.exists(keyfile)):
            print("ERROR: SSL is enabled but certificate or\
                   key does not exist.")
            return None, False, False, None, None

        return path, reread_on_query, ssl_enabled, certfile, keyfile
    except KeyError as e:
        print(f"ERROR: Missing key {e} in {config_path}.")
        return None, False, False, None, None


def preprocess_file(path: str) -> Optional[set]:
    try:
        with open(path, "r", encoding="utf-8") as file:
            return set(line.strip() for line in file)
    except Exception as e:
        print(f"ERROR: Failed to read file: {str(e)}")
        return None


def sanitize_query(query: str) -> str:
    # Sanitize query to prevent harmful characters or patterns
    return query.replace("..", "").replace("/", "").replace("\\", "")


def search_string_in_file(path: str, query: str) -> str:
    global cached_lines
    if len(query) > MAX_QUERY_LENGTH:
        return "ERROR: QUERY TOO LONG"

    if not query.strip():
        return "ERROR: EMPTY QUERY"

    query = sanitize_query(query)  # To prevent directory traversal

    if not os.path.exists(path):
        return "ERROR: FILE NOT FOUND"

    if cached_lines is None:
        cached_lines = preprocess_file(path)

    if cached_lines is None:
        return "ERROR: Failed to load file for searching."

    return "STRING EXISTS" if query in cached_lines else "STRING NOT FOUND"


def log_search(query: str, addr: str, exe_time: float, response: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{timestamp}, Query: '{query}', IP: {addr},\
        Execution Time: {exe_time}ms, Result: {response}\n"
    sys.stdout.write(log_entry)
    try:
        with open("server_log.txt", "a") as log_file:
            log_file.write(log_entry)
    except Exception as e:
        print(f"Failed to write to log: {str(e)}")


def rate_limit_exceeded(addr: str) -> bool:
    now = time.time()
    with rate_limit_lock:  # Ensuring thread safety while
        client_requests[addr] = [t for t in client_requests[addr]
                                 if now - t < RATE_WINDOW]
        if len(client_requests[addr]) >= RATE_LIMIT:
            return True
        client_requests[addr].append(now)
    return False


def handle_client(conn: socket.socket, addr: Tuple[str, int]) -> None:
    print(f"New connection from {addr}")
    conn.sendall(b"Hello, you are connected to the server!\n")

    try:
        while True:
            received_raw = conn.recv(BUFFER_SIZE)
            if not received_raw:
                break
            received_data = received_raw.decode("utf-8")
            # If the message is empty after stripping,
            # send an error instead of disconnecting
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
                log_search(received_data.strip(), f"{addr[0]}:{addr[1]}",
                           exe_time, response)

            conn.sendall(f"{response}\n".encode("utf-8"))
    except ConnectionResetError:
        print(f"WARNING: Client {addr} disconnected unexpectedly.")
    except Exception as e:
        print(f"ERROR: Unexpected error with client {addr}: {str(e)}")
    finally:
        conn.close()


def start_server() -> None:
    global path, REREAD_ON_QUERY, SSL_ENABLED, CERTFILE, KEYFILE
    path, REREAD_ON_QUERY, SSL_ENABLED, CERTFILE, KEYFILE = load_config()

    if path is None:
        print("ERROR: Invalid configuration. Server cannot start.")
        return

    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen()
        print(f"Server is listening on {HOST}:{PORT}...")

        ssl_context = None
        if SSL_ENABLED:
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(certfile=CERTFILE, keyfile=KEYFILE)
            ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
            print("SSL is enabled for the server.")

        while True:
            conn, addr = server.accept()

            if SSL_ENABLED and ssl_context:
                try:
                    conn = ssl_context.wrap_socket(conn, server_side=True)
                except ssl.SSLError as e:
                    print(f"SSL error with client {addr}: {e}")
                    conn.close()
                    continue

            threading.Thread(target=handle_client, args=(conn, addr),
                             daemon=True).start()
    except OSError as e:
        print(f"ERROR: Failed to start server. Possible cause: {e}")
    except KeyboardInterrupt:
        print("\nServer shutting down gracefully...")
    finally:
        server.close()


if __name__ == "__main__":
    start_server()
