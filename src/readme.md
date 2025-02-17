# Secure Search Service

This project implements a secure search service where a client can send queries to a server, and the server responds with the search results from a file. The server supports SSL encryption for secure communication, and both server and client configurations can be customized using respective configuration files.

## Requirements

### Prerequisites

- Python 3.7 or higher
- Required Python packages:
  - `socket`
  - `ssl`
  - `configparser`
  - `os`
  - `threading`
  - `time`
  - `unittest`
  - `pytest`
  - `matplotlib`

You can install the necessary dependencies by running:

pip install -r requirements.txt




Ensure you have the cert.pem and key.pem files in the same folder ready for SSL encryption.


Run the server script:
python server.py


## Using systemd for Daemonization:
Create a new service file in /etc/systemd/system:


sudo nano /etc/systemd/system/secure-search.service

Reload the systemd service manager:
sudo systemctl daemon-reload


## Enable the service to start on boot:
sudo systemctl enable secure-search.service

## Start the service:
sudo systemctl start secure-search.service


## Check the status of the service:
sudo systemctl status secure-search.service


## Start the Client
python client.py

## Benchmarking
You can benchmark the execution times of the search service for different file sizes by running the tests:

pytest test_benchmark.py


## Logging
Server logs are stored in server_log.txt. You can find information about search queries and their execution times there.