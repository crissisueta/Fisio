# Debian Server Setup Guide - Fisio Project

This guide will walk you through setting up a Debian server to run the Fisio Django application.

## Prerequisites

- Fresh Debian 11 or 12 server with root/sudo access
- Domain name (optional, for SSL)
- SSH access to the server

---

## 1. Initial Server Setup

```bash
# Update system packages
sudo apt update
sudo apt upgrade -y

# Install essential build tools and dependencies
sudo apt install -y \
    build-essential \
    libpq-dev \
    postgresql \
    postgresql-contrib \
    python3-pip \
    python3-dev \
    python3-venv \
    git \
    curl \
    wget \
    nano \
    nginx \
    certbot \
    python3-certbot-nginx \
    supervisor

# Create application user
    sudo useradd -m -s /bin/bash fisio
```

---

## 2. PostgreSQL Database Setup

```bash
# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE fisio_db;
CREATE USER fisio_user WITH PASSWORD 'your_secure_password_here';
ALTER ROLE fisio_user SET client_encoding TO 'utf8';
ALTER ROLE fisio_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE fisio_user SET default_transaction_deferrable TO on;
ALTER ROLE fisio_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE fisio_db TO fisio_user;
\q
EOF
```

---

## 3. Application Deployment

```bash
# Switch to application user
sudo su - fisio

# Clone or download the project
cd ~
git clone <your-repo-url> fisio_project
# OR if uploading manually:
# cd ~/fisio_project

cd ~/fisio_project

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
pip install -r requirements.txt
```

---

## 4. Environment Configuration

```bash
# Create .env file in project root
nano ~/fisio_project/.env
```

Add the following content:

```env
DEBUG=False
DJANGO_SECRET_KEY=your-secret-key-change-this-to-something-random
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,your-server-ip
CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://www.your-domain.com
DATABASE_URL=postgresql://fisio_user:your_secure_password_here@localhost:5432/fisio_db
```

Generate a secure secret key:
```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## 5. Django Setup

```bash
# Still as fisio user, in virtual environment
cd ~/fisio_project

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate
#Charlene@Hab2026
# Create superuser (optional, for admin access)
python manage.py createsuperuser
```

---

## 6. Gunicorn Configuration

```bash
# Test Gunicorn
cd ~/fisio_project
source venv/bin/activate
gunicorn fisio_project.wsgi:application --bind 127.0.0.1:8000

# Press Ctrl+C to stop
```

Create a Systemd service file for Gunicorn:

```bash
sudo nano /etc/systemd/system/gunicorn-fisio.service
```

Add the following content:

```ini
[Unit]
Description=Gunicorn application server for Fisio
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=notify
User=fisio
Group=www-data
WorkingDirectory=/home/fisio/fisio_project
EnvironmentFile=/home/fisio/fisio_project/.env
ExecStart=/home/fisio/fisio_project/venv/bin/gunicorn \
    --workers 3 \
    --worker-class sync \
    --bind unix:/home/fisio/fisio_project/gunicorn.sock \
    fisio_project.wsgi:application
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable gunicorn-fisio
sudo systemctl start gunicorn-fisio
sudo systemctl status gunicorn-fisio
```

---

## 7. Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/fisio
```

Add the following configuration:

```nginx
upstream gunicorn_fisio {
    server unix:/home/fisio/fisio_project/gunicorn.sock fail_timeout=0;
}

server {
    listen 80;
    server_name your-domain.com www.your-domain.com your-server-ip;
    client_max_body_size 20M;

    location /static/ {
        alias /home/fisio/fisio_project/staticfiles/;
        expires 30d;
    }

    location /media/ {
        alias /home/fisio/fisio_project/media/;
        expires 7d;
    }

    location / {
        proxy_pass http://gunicorn_fisio;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_read_timeout 60s;
        proxy_connect_timeout 60s;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/fisio /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

---

## 8. SSL/HTTPS with Let's Encrypt

```bash
# Install certificate (replace with your domain)
sudo certbot certonly --nginx -d your-domain.com -d www.your-domain.com

# Update Nginx configuration with SSL
sudo nano /etc/nginx/sites-available/fisio
```

Replace the server block with:

```nginx
upstream gunicorn_fisio {
    server unix:/home/fisio/fisio_project/gunicorn.sock fail_timeout=0;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;
    client_max_body_size 20M;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location /static/ {
        alias /home/fisio/fisio_project/staticfiles/;
        expires 30d;
    }

    location /media/ {
        alias /home/fisio/fisio_project/media/;
        expires 7d;
    }

    location / {
        proxy_pass http://gunicorn_fisio;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_read_timeout 60s;
        proxy_connect_timeout 60s;
    }
}
```

Verify and reload:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

Setup auto-renewal:

```bash
sudo certbot renew --dry-run
sudo systemctl enable certbot.timer
```

---

## 9. Firewall Setup

```bash
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 5432/tcp from 127.0.0.1
```

---

## 10. Monitoring and Logs

```bash
# View Gunicorn logs
sudo journalctl -u gunicorn-fisio -f

# View Nginx logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log

# Check service status
sudo systemctl status gunicorn-fisio
sudo systemctl status nginx
sudo systemctl status postgresql
```

---

## 11. Deployment Updates

When you need to update the application:

```bash
# SSH into server
ssh fisio@your-server-ip

cd ~/fisio_project
source venv/bin/activate

# Pull latest code
git pull origin main

# Install any new dependencies
pip install -r requirements.txt

# Run migrations if needed
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Restart Gunicorn
sudo systemctl restart gunicorn-fisio
```

---

## 12. Backup Strategy

Create a backup script:

```bash
sudo nano /usr/local/bin/backup-fisio.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/home/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Backup database
pg_dump -U fisio_user fisio_db | gzip > $BACKUP_DIR/fisio_db_$DATE.sql.gz

# Backup media files
tar -czf $BACKUP_DIR/fisio_media_$DATE.tar.gz /home/fisio/fisio_project/media/

# Keep only last 30 days of backups
find $BACKUP_DIR -name "fisio_db_*.sql.gz" -mtime +30 -delete
find $BACKUP_DIR -name "fisio_media_*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

Make it executable:

```bash
sudo chmod +x /usr/local/bin/backup-fisio.sh
```

Add to crontab for daily backups at 2 AM:

```bash
sudo crontab -e
```

Add:
```
0 2 * * * /usr/local/bin/backup-fisio.sh
```

---

## Troubleshooting

### Check if Gunicorn is running
```bash
sudo systemctl status gunicorn-fisio
```

### Check if Nginx is running
```bash
sudo systemctl status nginx
```

### Test database connection
```bash
psql -U fisio_user -d fisio_db -h localhost
```

### View application errors
```bash
sudo journalctl -u gunicorn-fisio -n 50
```

### Restart all services
```bash
sudo systemctl restart gunicorn-fisio nginx postgresql
```

---

## Quick Reference Commands

```bash
# Check services
sudo systemctl status gunicorn-fisio nginx postgresql

# Restart services
sudo systemctl restart gunicorn-fisio
sudo systemctl restart nginx

# View logs
sudo journalctl -u gunicorn-fisio -f
sudo tail -f /var/log/nginx/error.log

# Database management
sudo -u postgres psql -d fisio_db -U fisio_user

# Collect static files after code update
cd ~/fisio_project && source venv/bin/activate && python manage.py collectstatic --noinput
```

---

## Security Best Practices

1. **Change PostgreSQL password** from default after setup
2. **Use strong SECRET_KEY** in .env
3. **Set DEBUG=False** in production
4. **Use HTTPS** always (Let's Encrypt is free)
5. **Keep packages updated**: `sudo apt update && sudo apt upgrade`
6. **Configure firewall** properly
7. **Set up automated backups**
8. **Monitor disk space** and logs
9. **Use SSH keys** instead of passwords
10. **Regularly review logs** for suspicious activity

---

This setup provides a production-ready deployment of your Fisio Django application on Debian.
