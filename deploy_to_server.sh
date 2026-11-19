#!/usr/bin/env bash
# [File 06] Ubuntu/Debian Cloud Server Production Deployment Script
set -e

APP_DIR="/opt/samagamtransport"
SERVICE_NAME="samagamtransport"

echo "🚀 Deploying Samagam Transport Platform to $APP_DIR ..."

sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip nginx

sudo mkdir -p "$APP_DIR"
sudo cp -r . "$APP_DIR"
cd "$APP_DIR"

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

python3 seed_test_data.py

sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<EOF
[Unit]
Description=Samagam Transport & Logistics FastAPI Server
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo chown -R www-data:www-data "$APP_DIR"
sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}
sudo systemctl restart ${SERVICE_NAME}

sudo cp samagamtransport_nginx.conf /etc/nginx/sites-available/samagamtransport
sudo ln -sf /etc/nginx/sites-available/samagamtransport /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx

echo "✅ Deployment complete! Server is live on Port 80."