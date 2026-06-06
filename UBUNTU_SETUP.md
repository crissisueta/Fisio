# Ubuntu Server Setup

This project includes `setup-ubuntu-server.sh`, an automated installer based on `DEBIAN_SETUP.md`.

Ubuntu does not have an official `24.02` server release. Use Ubuntu Server `24.04 LTS` if possible.

## 1. Copy the Project to the Server

Upload or clone this repository on the server, then enter the project folder:

```bash
cd /path/to/Fisio
```

## 2. Run the Installer

For a server without a domain yet:

```bash
chmod +x setup-ubuntu-server.sh
sudo -E ./setup-ubuntu-server.sh
```

For a domain with HTTPS:

```bash
chmod +x setup-ubuntu-server.sh
sudo -E ./setup-ubuntu-server.sh \
  --domain "example.com www.example.com" \
  --email admin@example.com \
  --ssl
```

The script installs system packages, PostgreSQL, Nginx, Gunicorn, Python dependencies, the Django `.env`, migrations, static files, firewall rules, and a daily backup script.

## Useful Options

```bash
# Use a custom SSH port before enabling UFW
sudo -E SSH_PORT=2222 ./setup-ubuntu-server.sh

# Clone directly from a Git repository instead of copying the current folder
sudo -E ./setup-ubuntu-server.sh --repo-url https://github.com/you/fisio.git --repo-branch main

# Provide your own database password and Django secret
sudo -E DB_PASSWORD='change-me' DJANGO_SECRET_KEY='change-me-too' ./setup-ubuntu-server.sh

# Skip firewall, backups, or apt upgrade
sudo -E ./setup-ubuntu-server.sh --no-ufw --no-backups --no-upgrade
```

## 3. Create the Django Admin User

After installation:

```bash
sudo -u fisio -H bash -lc 'cd /home/fisio/fisio_project && source venv/bin/activate && python manage.py createsuperuser'
```

## 4. Check Services

```bash
sudo systemctl status gunicorn-fisio
sudo systemctl status nginx
sudo journalctl -u gunicorn-fisio -f
sudo tail -f /var/log/nginx/error.log
```

The generated production environment is saved at:

```bash
/home/fisio/fisio_project/.env
```

## 5. Updating Later

```bash
sudo -u fisio -H git -C /home/fisio/fisio_project pull --ff-only
sudo -u fisio -H /home/fisio/fisio_project/venv/bin/pip install -r /home/fisio/fisio_project/requirements.txt
sudo -u fisio -H bash -lc 'cd /home/fisio/fisio_project && venv/bin/python manage.py migrate && venv/bin/python manage.py collectstatic --noinput'
sudo systemctl restart gunicorn-fisio
```
