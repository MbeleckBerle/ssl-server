import configparser
import os
import socket
import ssl
import threading
import time
import sys
from datetime import datetime
from typing import Optional, Tuple


HOST: str = "0.0.0.0"
PORT: int = 44445
path: Optional[str] = None
REREAD_ON_QUERY: bool = False
SSL_ENABLED: bool = False
CERTFILE: Optional[str] = None
KEYFILE: Optional[str] = None
BUFFER_SIZE: int = 1024
cached_lines: Optional[set] = None


def load_config(config_path: str = "config.ini") -> Tuple[Optional[str],
                                                          bool, bool,
                                                          Optional[str],
                                                          Optional[str]]:
    """
    Loads the server configuration from the given INI file.

    Parameters:
        config_path (str): The path to the configuration file.
        Defaults to 'config.ini'.

    Returns:
        Tuple: Contains the file path, reread option, SSL status,
        certificate file, and key file.
    """
    if not os.path.exists(config_path):
        print(f"ERROR: Configuration file '{config_path}'\
            not found. Please create it.")
        return None, False, False, None, None

    config = configparser.ConfigParser()
    config.read(config_path)

    try:
        path: str = config["DEFAULT"]["linuxpath"]
        reread_on_query: bool = (
            config["DEFAULT"].get("REREAD_ON_QUERY", "False")
            .strip()
            .lower() == "true"
        )
        ssl_enabled: bool = (
            config["DEFAULT"].get("SSL_ENABLED", "False")
            .strip()
            .lower() == "true"
        )
        certfile: str = config["DEFAULT"].get("CERTFILE", "")
        keyfile: str = config["DEFAULT"].get("KEYFILE", "")

        if not os.path.exists(path):
            print(f"ERROR: Configured file '{path}' \
                  does not exist. Check 'linuxpath' in {config_path}.")
            return None, False, False, None, None

        if ssl_enabled:
            if not os.path.exists(certfile) or not os.path.exists(keyfile):
                print(f"ERROR: SSL is enabled but certificate '{certfile}'\
                      or key '{keyfile}' does not exist.")
                return None, False, False, None, None

        return path, reread_on_query, ssl_enabled, certfile, keyfile

    except KeyError as e:
        print(f"ERROR: Missing key {e} in {config_path}.\
              Ensure all required keys are present.")
        return None, False, False, None, None


def preprocess_file(path: str) -> Optional[set]:
    try:
        with open(path, "r", encoding="utf-8") as file:
            lines = set(line.strip() for line in file)
        return lines
    except Exception as e:
        print(f"ERROR: Failed to read file: {str(e)}")
        return None


def search_string_in_file(path: str, query: str, reread_on_query: bool) -> str:
    global cached_lines

    if not query.strip():
        return "ERROR: EMPTY QUERY"

    if not os.path.exists(path):
        return "ERROR: FILE NOT FOUND"

    if cached_lines is None:
        cached_lines = preprocess_file(path)

    if cached_lines is None:
        return "ERROR: Failed to load file for searching."

    if query in cached_lines:
        return "STRING EXISTS"
    else:
        return "STRING NOT FOUND"


def log_search(query: str, addr: str, exe_time: float, response: str) -> None:
    timestamp: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry: str = (
        f"DEBUG: {timestamp}, Query: '{query}', IP: {addr}, "
        f"Execution Time: {exe_time}ms, Result: {response}\n"
    )
    sys.stdout.write(log_entry)
    try:
        with open("server_log.txt", "a") as log_file:
            log_file.write(log_entry)
    except Exception as e:
        print(f"ERROR: Failed to write to log file: {str(e)}")


def handle_client(conn: socket.socket, addr: Tuple[str, int]) -> None:
    print(f"New connection from {addr}")
    conn.sendall(b"Hello, you are connected to the server!\n")

    MAX_DATA_SIZE = 1048576  # 1MB max data size

    while True:
        try:
            received_data = b""
            while True:
                chunk = conn.recv(BUFFER_SIZE)
                received_data += chunk
                if len(chunk) < BUFFER_SIZE:
                    break

                if len(received_data) > MAX_DATA_SIZE:
                    response = "ERROR: DATA TOO LARGE"
                    conn.sendall(f"{response}\n".encode("utf-8"))
                    conn.close()
                    return

            data = received_data.decode("utf-8").strip()

            if not data:
                response = "ERROR: EMPTY QUERY"
            else:
                start_time = time.time()
                response = search_string_in_file(path, data, REREAD_ON_QUERY)
                exe_time = round((time.time() - start_time) * 1000, 3)
                log_search(data, f"{addr[0]}:{addr[1]}", exe_time, response)

            conn.sendall(f"{response}\n".encode("utf-8"))

        except ConnectionResetError:
            print(f"WARNING: Client {addr} disconnected unexpectedly.")
            break
        except Exception as e:
            print(f"ERROR: Unexpected error with client {addr}: {str(e)}")
            break

    conn.close()


def start_server() -> None:
    global path, REREAD_ON_QUERY, SSL_ENABLED, CERTFILE, KEYFILE
    path, REREAD_ON_QUERY, SSL_ENABLED, CERTFILE, KEYFILE = load_config()

    if path is None:
        print("ERROR: Invalid configuration. Server cannot start.")
        return

    try:
        server: socket.socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
            )
        server.setsockopt(socket.SOL_SOCKET,
                          socket.SO_REUSEADDR,
                          1
                          )
        server.bind((
            HOST,
            PORT
            ))
        server.listen()
        print(f"Server is listening on {HOST}:{PORT}...")

        ssl_context: Optional[ssl.SSLContext] = None
        if SSL_ENABLED:
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(
                certfile=CERTFILE,
                keyfile=KEYFILE
                )
            print("SSL is enabled for the server.")

        while True:
            conn, addr = server.accept()

            if SSL_ENABLED and ssl_context is not None:
                try:
                    conn = ssl_context.wrap_socket(
                        conn,
                        server_side=True
                        )
                except ssl.SSLError as e:
                    print(f"SSL error with client {addr}: {e}")
                    conn.close()
                    continue

            threading.Thread(
                target=handle_client,
                args=(conn, addr),
                daemon=True
            ).start()

    except OSError as e:
        print(f"ERROR: Failed to start server. Possible cause: {e}")
    except KeyboardInterrupt:
        print("\nServer shutting down gracefully...")
    finally:
        server.close()


if __name__ == "__main__":
    start_server()
