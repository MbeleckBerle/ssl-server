# Secure Search Service

This project implements a secure search service where a client can send queries to a server, and the server responds with the search results from a file. The server supports SSL encryption for secure communication, and both server and client configurations can be customized using respective configuration files.


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

## on linux Run 
sudo apt-get install openssl

## On macOS run
brew install openssl


## Generate the SSL Certificate and Key Files
You can generate the self-signed SSL certificate (cert.pem) and the private key (key.pem) using the following OpenSSL command:

openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout key.pem -out cert.pem

## Update Your Configuration
[DEFAULT]
linuxpath = /path/to/your/file.txt
REREAD_ON_QUERY = True
SSL_ENABLED = True
CERTFILE = /path/to/cert.pem
KEYFILE = /path/to/key.pem


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