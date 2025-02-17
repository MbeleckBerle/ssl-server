#!/usr/bin/env python3
"""
Client module for the secure search service.

This module connects to the search server and allows interactive query submission.
SSL authentication is optional and configurable via a client configuration file.
"""

import socket
import ssl
import configparser
import os
from typing import Tuple

def load_client_config(config_path: str = "client_config.ini") -> Tuple[bool, str]:
    """
    Load client configuration from a file.

    The config file should have:
      - SSL_ENABLED: whether SSL is enabled (True/False).
      - SERVER_CERT: path to the server certificate (if SSL is enabled).

    :param config_path: Path to the client configuration file.
    :return: Tuple of (ssl_enabled, server_cert).
    """
    ssl_enabled: bool = False
    server_cert: str = ""
    if os.path.exists(config_path):
        config = configparser.ConfigParser()
        config.read(config_path)
        ssl_enabled = config["DEFAULT"].get("SSL_ENABLED", "False").strip().lower() == "true"
        server_cert = config["DEFAULT"].get("SERVER_CERT", "")
    return ssl_enabled, server_cert

def run_client(server_host: str, server_port: int) -> None:
    """
    Connects to the server, sends queries, and prints responses.

    :param server_host: The server hostname or IP address.
    :param server_port: The server port.
    """
    ssl_enabled, server_cert = load_client_config()

    try:
        client_socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if ssl_enabled:
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            if server_cert and os.path.exists(server_cert):
                context.load_verify_locations(cafile=server_cert)
            else:
                # For self-signed certificates without a provided CA file:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            client_socket = context.wrap_socket(client_socket, server_hostname=server_host)
            print("SSL is enabled for the client.")

        client_socket.connect((server_host, server_port))
        print(f"Connected to server at {server_host}:{server_port}")

        # Receive and display the server's greeting.
        greeting: str = client_socket.recv(1024).decode("utf-8").strip()
        print("Server:", greeting)

        while True:
            query: str = input("Enter your query (or 'exit' to quit): ").strip()
            if query.lower() == "exit":
                print("Exiting client.")
                break

            if not query:
                print("Empty query—please enter a valid string.")
                continue

            client_socket.sendall(query.encode("utf-8"))
            response: str = client_socket.recv(4096).decode("utf-8")
            if not response:
                print("No response received from server. Exiting.")
                break
            print("Response:\n" + response)

    except ConnectionRefusedError:
        print("Connection refused. Is the server running?")
    except Exception as e:
        print("An error occurred:", str(e))
    finally:
        try:
            client_socket.close()
        except Exception:
            pass

if __name__ == "__main__":
    # Connect to localhost at the default port.
    HOST: str = "127.0.0.1"
    PORT: int = 44446
    run_client(HOST, PORT)
