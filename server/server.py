import socket
import threading
import configparser
import time
import os
from datetime import datetime

# Todo
### 1. config
### 2. search string in file
### 3. log search
### 4. client

### 5. unit test

# Load configuration 
def load_config(config_path="config.ini"):
    """Load server configuration from file."""
    if not os.path.exists(config_path):
        print(f"ERROR: Configuration file '{config_path}' not found. Please create it.")
        return None, None

    config = configparser.ConfigParser()
    config.read(config_path)

    try:
        file_path = config["DEFAULT"]["linuxpath"]
        reread_on_query = config["DEFAULT"].get("REREAD_ON_QUERY", "False").strip().lower() == "true"

        if not os.path.exists(file_path):
            print(f"ERROR: Configured file '{file_path}' does not exist. Check 'linuxpath' in {config_path}.")
            return None, None

        return file_path, reread_on_query

    except KeyError as e:
        print(f"ERROR: Missing key {e} in {config_path}. Ensure all required keys are present.")
        return None, None

# Server configuration
HOST = "0.0.0.0"
PORT = 44445
FILE_PATH, REREAD_ON_QUERY = load_config()

# Search function with error handling
def search_string_in_file(file_path, query, reread_on_query):
    """Search for an exact string match in the file with error handling."""
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

# Caching function with thread safety
def search_string_in_file_cached(file_path, query):
    """Caches the file content for optimized searching."""
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

# Logging function
def log_search(query, addr, execution_time, response):
    """Logs search queries into a server log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"DEBUG: {timestamp}, Query: '{query}', IP: {addr}, Time: {execution_time}ms, Result: {response}\n"
    
    print(log_entry.strip())  # Log to console
    try:
        with open("server_log.txt", "a") as log_file:
            log_file.write(log_entry)
    except Exception as e:
        print(f"ERROR: Failed to write to log file: {str(e)}")

# Client handler function
def handle_client(conn, addr):
    """Handles client requests with error handling."""
    print(f"New connection from {addr}")
    conn.sendall(b"Hello, you are connected to the server!\n")

    while True:
        try:
            data = conn.recv(1024).rstrip(b'\x00').decode("utf-8").strip()

            if data == "":  # Handle blank input
                response = "ERROR: EMPTY QUERY"
            else:
                start_time = time.time()
                response = search_string_in_file(FILE_PATH, data, REREAD_ON_QUERY)
                execution_time = round((time.time() - start_time) * 1000, 3)
                log_search(data, addr, execution_time, response)

            conn.sendall(f"{response}\n".encode("utf-8"))
        except ConnectionResetError:
            print(f"WARNING: Client {addr} disconnected unexpectedly.")
            break
        except Exception as e:
            print(f"ERROR: Unexpected error with client {addr}: {str(e)}")
            break

    conn.close()

# Start the server with improved error handling
def start_server():
    """Initializes and starts the TCP server."""
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen()
        print(f"Server is listening on {HOST}:{PORT}...")

        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

    except OSError as e:
        print(f"ERROR: Failed to start server. Possible cause: {e}")
    except KeyboardInterrupt:
        print("\nServer shutting down gracefully...")
    finally:
        server.close()

if __name__ == "__main__":
    if FILE_PATH is None:
        print("ERROR: Invalid configuration. Server cannot start.")
    else:
        start_server()
