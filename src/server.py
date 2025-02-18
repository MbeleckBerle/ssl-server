
"""
Server module for the secure search service.

This module implements a TCP server that:
  - Loads configuration from a file.
  - Searches for a query string in a file.
  - Logs search queries.
  - Optionally uses SSL for secure communications with clients.

The code is statically typed, PEP8 and PEP20 compliant, and fully documented.
"""

import socket
import threading
import configparser
import time
import os
import ssl
from datetime import datetime
from typing import Optional, Tuple

# Global configuration variables (populated by load_config)
HOST: str = "0.0.0.0"
PORT: int = 44445
FILE_PATH: Optional[str] = None
REREAD_ON_QUERY: bool = False
SSL_ENABLED: bool = False
CERTFILE: Optional[str] = None
KEYFILE: Optional[str] = None

def load_config(config_path: str = "config.ini") -> Tuple[Optional[str], bool, bool, Optional[str], Optional[str]]:
    """
    Load server configuration from a config file.

    The config file must define at least the following keys under the DEFAULT section:
      - linuxpath: path to the file to search.
      - REREAD_ON_QUERY: whether to reread the file on every query (True/False).
      - SSL_ENABLED: whether SSL is enabled for secure communications (True/False).
      - CERTFILE: path to the SSL certificate (if SSL_ENABLED is True).
      - KEYFILE: path to the SSL key (if SSL_ENABLED is True).

    :param config_path: Path to the configuration file.
    :return: Tuple containing (file_path, reread_on_query, ssl_enabled, certfile, keyfile).
    """
    if not os.path.exists(config_path):
        print(f"ERROR: Configuration file '{config_path}' not found. Please create it.")
        return None, False, False, None, None

    config = configparser.ConfigParser()
    config.read(config_path)

    try:
        file_path: str = config["DEFAULT"]["linuxpath"]
        reread_on_query: bool = config["DEFAULT"].get("REREAD_ON_QUERY", "False").strip().lower() == "true"
        ssl_enabled: bool = config["DEFAULT"].get("SSL_ENABLED", "False").strip().lower() == "true"
        certfile: str = config["DEFAULT"].get("CERTFILE", "")
        keyfile: str = config["DEFAULT"].get("KEYFILE", "")

        if not os.path.exists(file_path):
            print(f"ERROR: Configured file '{file_path}' does not exist. Check 'linuxpath' in {config_path}.")
            return None, False, False, None, None

        if ssl_enabled:
            if not os.path.exists(certfile) or not os.path.exists(keyfile):
                print(f"ERROR: SSL is enabled but certificate '{certfile}' or key '{keyfile}' does not exist.")
                return None, False, False, None, None

        return file_path, reread_on_query, ssl_enabled, certfile, keyfile

    except KeyError as e:
        print(f"ERROR: Missing key {e} in {config_path}. Ensure all required keys are present.")
        return None, False, False, None, None

def search_string_in_file(file_path: str, query: str, reread_on_query: bool) -> str:
    """
    Search for an exact string match in the file with error handling.

    :param file_path: Path to the file to be searched.
    :param query: Query string to search for.
    :param reread_on_query: Flag to indicate whether to reread the file on every query.
    :return: "STRING EXISTS", "STRING NOT FOUND", or an error message.
    """
    if not query.strip():
        return "ERROR: EMPTY QUERY"

    if not os.path.exists(file_path):
        return "ERROR: FILE NOT FOUND"

    try:
        if reread_on_query:
            with open(file_path, "r", encoding="utf-8") as file:
                for line in file:
                    if line.strip() == query:
                        return "STRING EXISTS"
            return "STRING NOT FOUND"
        else:
            return search_string_in_file_cached(file_path, query)
    except PermissionError:
        return f"ERROR: Permission denied when accessing '{file_path}'."
    except Exception as e:
        return f"ERROR: {str(e)}"

def search_string_in_file_cached(file_path: str, query: str) -> str:
    """
    Caches the file content for optimized searching.

    :param file_path: Path to the file.
    :param query: Query string to search for.
    :return: "STRING EXISTS", "STRING NOT FOUND", or an error message.
    """
    if not hasattr(search_string_in_file_cached, "cached_lines"):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                search_string_in_file_cached.cached_lines = file.readlines()
        except Exception as e:
            return f"ERROR: Failed to read file: {str(e)}"

    for line in search_string_in_file_cached.cached_lines:
        if line.strip() == query:
            return "STRING EXISTS"
    return "STRING NOT FOUND"

def log_search(query: str, addr: str, execution_time: float, response: str) -> None:
    """
    Logs search queries into a server log file.

    :param query: The search query.
    :param addr: The client IP address (and port).
    :param execution_time: Execution time in milliseconds.
    :param response: The result of the search.
    """
    timestamp: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry: str = f"DEBUG: {timestamp}, Query: '{query}', IP: {addr}, Time: {execution_time}ms, Result: {response}\n"
    print(log_entry.strip())  # Also log to console
    try:
        with open("server_log.txt", "a") as log_file:
            log_file.write(log_entry)
    except Exception as e:
        print(f"ERROR: Failed to write to log file: {str(e)}")

def handle_client(conn: socket.socket, addr: Tuple[str, int]) -> None:
    """
    Handles a client connection: receives queries, processes them, and sends responses.

    :param conn: The client socket.
    :param addr: The client address as a tuple.
    """
    print(f"New connection from {addr}")
    conn.sendall(b"Hello, you are connected to the server!\n")

    while True:
        try:
            data: str = conn.recv(1024).rstrip(b'\x00').decode("utf-8").strip()
            if data == "":
                response: str = "ERROR: EMPTY QUERY"
            else:
                start_time: float = time.time()
                response = search_string_in_file(FILE_PATH, data, REREAD_ON_QUERY)
                execution_time: float = round((time.time() - start_time) * 1000, 3)
                log_search(data, f"{addr[0]}:{addr[1]}", execution_time, response)

            conn.sendall(f"{response}\n".encode("utf-8"))
        except ConnectionResetError:
            print(f"WARNING: Client {addr} disconnected unexpectedly.")
            break
        except Exception as e:
            print(f"ERROR: Unexpected error with client {addr}: {str(e)}")
            break

    conn.close()

def start_server() -> None:
    """
    Initializes and starts the TCP server. If SSL is enabled in the configuration,
    the server uses SSL for secure client communications.
    """
    global FILE_PATH, REREAD_ON_QUERY, SSL_ENABLED, CERTFILE, KEYFILE
    FILE_PATH, REREAD_ON_QUERY, SSL_ENABLED, CERTFILE, KEYFILE = load_config()
    if FILE_PATH is None:
        print("ERROR: Invalid configuration. Server cannot start.")
        return

    try:
        server: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen()
        print(f"Server is listening on {HOST}:{PORT}...")

        ssl_context: Optional[ssl.SSLContext] = None
        if SSL_ENABLED:
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(certfile=CERTFILE, keyfile=KEYFILE)
            print("SSL is enabled for the server.")

        while True:
            conn, addr = server.accept()
            if SSL_ENABLED and ssl_context is not None:
                try:
                    conn = ssl_context.wrap_socket(conn, server_side=True)
                except ssl.SSLError as e:
                    print(f"SSL error with client {addr}: {e}")
                    conn.close()
                    continue

            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

    except OSError as e:
        print(f"ERROR: Failed to start server. Possible cause: {e}")
    except KeyboardInterrupt:
        print("\nServer shutting down gracefully...")
    finally:
        server.close()

if __name__ == "__main__":
    start_server()
