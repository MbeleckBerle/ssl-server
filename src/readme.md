## 1. Install Dependencies

Ensure Python is installed, then install any required dependencies.

[DEFAULT]
SSL_ENABLED=True  # Change to False if SSL is not needed
SERVER_CERT=cert.pem  # Path to server certificate if using SSL



## 2. Configure the Client

Edit client_config.ini to set up SSL and server details.

[DEFAULT]
SSL_ENABLED=True  # Change to False if SSL is not needed
SERVER_CERT=cert.pem  # Path to server certificate if using SSL



## 3. Create a Systemd Service

Create a new systemd service file. make sure to replace the paths with the your paths:
the user and the group are your username

sudo nano /etc/systemd/system/secure_search_client.service

Add the following content:

[Unit]
Description=Secure Search Client Daemon
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/$USER/secure_search_client/client.py --config /home/$USER/secure_search_client/client_config.ini
WorkingDirectory=/home/$USER/secure_search_client
Restart=always
User=$USER
Group=$USER
StandardOutput=append:/home/$USER/secure_search_client/client.log
StandardError=append:/home/$USER/secure_search_client/client_error.log

[Install]
WantedBy=multi-user.target


## 4. Reload and Start the Service

sudo systemctl daemon-reload
sudo systemctl enable secure_search_client.service
sudo systemctl start secure_search_client.service



## 5. Verify the Service

Check the status of the service:
sudo systemctl status secure_search_client.service

To view logs:
journalctl -u secure_search_client.service -f



## 6. Stop or Restart the Service

To stop:
sudo systemctl stop secure_search_client.service

To restart:
sudo systemctl restart secure_search_client.service


Uninstallation

To remove the service:
sudo systemctl stop secure_search_client.service
sudo systemctl disable secure_search_client.service
sudo rm /etc/systemd/system/secure_search_client.service
sudo systemctl daemon-reload


Troubleshooting
journalctl -xe -u secure_search_client.service

Ensure the client script has execute permissions:
chmod +x /home/$USER/secure_search_client/client.py


Verify Python dependencies are installed.