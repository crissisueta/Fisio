# Fisio Django - Quick Deployment Checklist

Use this checklist for a smooth deployment of your Fisio application on Debian.

## Pre-Deployment (on your local machine)

- [ ] Commit all changes to git
- [ ] Test locally with `DEBUG=False`
- [ ] Verify all environment variables are properly configured
- [ ] Run tests: `python manage.py test`
- [ ] Check for unused imports and code quality

## Server Preparation

### Option 1: Automated Setup
```bash
# Upload the setup script to your server
scp setup-debian-server.sh root@your-server:/tmp/

# Connect to server
ssh root@your-server

# Make script executable and run
chmod +x /tmp/setup-debian-server.sh
/tmp/setup-debian-server.sh
```

### Option 2: Manual Setup
Follow the step-by-step instructions in [DEBIAN_SETUP.md](DEBIAN_SETUP.md)

## Post-Installation Configuration

### 1. Configure Environment Variables
```bash
sudo nano /home/fisio/fisio_project/.env
```

Set these values:
```env
DEBUG=False
DJANGO_SECRET_KEY=<generate with: python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())">
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,your-ip
CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://www.your-domain.com
DATABASE_URL=postgresql://fisio_user:password@localhost:5432/fisio_db
```

### 2. Configure Domain and SSL
```bash
# Point your domain DNS to your server IP

# Request SSL certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Auto-renewal should be configured automatically
sudo systemctl enable certbot.timer
```

### 3. Start Services
```bash
sudo systemctl start gunicorn-fisio
sudo systemctl start nginx
sudo systemctl start postgresql

# Verify all services are running
sudo systemctl status gunicorn-fisio
sudo systemctl status nginx
sudo systemctl status postgresql
```

### 4. Create Admin User
```bash
sudo su - fisio
cd ~/fisio_project
source venv/bin/activate
python manage.py createsuperuser
exit
```

### 5. Verify Deployment
- [ ] Visit http://your-domain.com - should redirect to HTTPS
- [ ] Visit https://your-domain.com - should show your application
- [ ] Check admin: https://your-domain.com/admin
- [ ] View logs: `sudo journalctl -u gunicorn-fisio -f`

## Deployment Updates

### For Code Updates:
```bash
# SSH to server
ssh fisio@your-server

cd ~/fisio_project
source venv/bin/activate

# Pull latest changes
git pull origin main

# Install any new packages
pip install -r requirements.txt

# Run migrations if needed
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Restart application
sudo systemctl restart gunicorn-fisio
```

### For Settings/Configuration Updates:
```bash
# Edit .env file
sudo nano /home/fisio/fisio_project/.env

# Restart application for changes to take effect
sudo systemctl restart gunicorn-fisio
```

## Essential Commands Reference

### Service Management
```bash
# Start/stop/restart services
sudo systemctl start gunicorn-fisio
sudo systemctl stop gunicorn-fisio
sudo systemctl restart gunicorn-fisio
sudo systemctl status gunicorn-fisio

# Same for Nginx and PostgreSQL
sudo systemctl restart nginx
sudo systemctl restart postgresql
```

### View Logs
```bash
# Application logs (real-time)
sudo journalctl -u gunicorn-fisio -f

# Last 50 lines
sudo journalctl -u gunicorn-fisio -n 50

# Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Nginx access logs
sudo tail -f /var/log/nginx/access.log
```

### Database Access
```bash
# Connect to database as fisio user
psql -U fisio_user -d fisio_db

# Useful PostgreSQL commands
\dt                    # List tables
\d table_name          # Describe table
SELECT * FROM table;   # Query table
\q                     # Quit
```

### Django Management
```bash
# SSH as fisio user
sudo su - fisio
cd ~/fisio_project
source venv/bin/activate

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput

# Run Django shell
python manage.py shell

# Create backup
python manage.py dumpdata > backup.json
```

### Monitoring
```bash
# Check disk space
df -h

# Check memory usage
free -h

# Check CPU usage
top

# Check running processes
ps aux | grep gunicorn
ps aux | grep nginx

# Check open ports
sudo netstat -tlnp
```

## Troubleshooting

### Application won't start
```bash
# Check logs
sudo journalctl -u gunicorn-fisio -n 30

# Check if socket file exists
ls -la /home/fisio/fisio_project/gunicorn.sock

# Try running gunicorn manually
sudo su - fisio
cd ~/fisio_project
source venv/bin/activate
gunicorn fisio_project.wsgi:application --bind 127.0.0.1:8000
```

### Database connection errors
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check database user exists
sudo -u postgres psql -l

# Test connection manually
psql -U fisio_user -d fisio_db -h localhost
```

### Nginx not working
```bash
# Check Nginx syntax
sudo nginx -t

# Check if Nginx is running
sudo systemctl status nginx

# Check Nginx logs
sudo tail -f /var/log/nginx/error.log

# Check if port 80/443 is in use
sudo netstat -tlnp | grep ':80\|:443'
```

### Static files not loading
```bash
# Collect static files again
cd ~/fisio_project
source venv/bin/activate
python manage.py collectstatic --noinput

# Check permissions
ls -la /home/fisio/fisio_project/staticfiles/

# Restart Nginx
sudo systemctl restart nginx
```

### SSL certificate issues
```bash
# Check certificate expiry
sudo certbot certificates

# Renew certificate manually
sudo certbot renew

# View renewal log
sudo tail -f /var/log/letsencrypt/letsencrypt.log
```

## Security Checklist

- [ ] Changed all default passwords
- [ ] Set DEBUG=False in production
- [ ] Generated strong DJANGO_SECRET_KEY
- [ ] Configured ALLOWED_HOSTS correctly
- [ ] Configured CSRF_TRUSTED_ORIGINS
- [ ] SSL/TLS certificate installed
- [ ] Firewall enabled and configured
- [ ] Regular backups configured
- [ ] PostgreSQL password is strong
- [ ] Database backups are stored securely
- [ ] SSH key authentication configured
- [ ] Password authentication disabled in SSH
- [ ] Database running on localhost only
- [ ] Static files served by Nginx (not Django)
- [ ] Media files uploaded to secure directory

## Performance Optimization

### Gunicorn Workers
Adjust workers based on CPU cores:
```bash
# Edit /etc/systemd/system/gunicorn-fisio.service
# --workers = (2 × CPU cores) + 1
# For 2 cores: --workers 5
# For 4 cores: --workers 9
```

### Database Optimization
```bash
# Monitor slow queries
sudo -u postgres psql -d fisio_db
SELECT * FROM pg_stat_statements ORDER BY mean_time DESC;
```

### Nginx Caching
```bash
# Already configured in the setup for static files (30 days)
# Media files cached for 7 days
```

## Backup and Recovery

### Daily Backups
Backups are configured to run daily at 2 AM.

### Manual Backup
```bash
/usr/local/bin/backup-fisio.sh
```

### Restore from Backup
```bash
# Database restore
gunzip -c /home/backups/fisio_db_*.sql.gz | psql -U fisio_user -d fisio_db

# Media files restore
tar -xzf /home/backups/fisio_media_*.tar.gz -C /
```

## Monitoring & Alerts

### Setup Email Alerts (optional)
Install and configure Monit or similar service for automatic alerts on service failures.

### Manual Health Check
```bash
#!/bin/bash
# Save as /usr/local/bin/health-check.sh

curl -s https://your-domain.com/admin/login/ > /dev/null
if [ $? -ne 0 ]; then
    echo "Application is down!" | mail -s "Alert" admin@example.com
fi

systemctl is-active --quiet gunicorn-fisio || systemctl restart gunicorn-fisio
```

## Documentation Links

- Django Documentation: https://docs.djangoproject.com/
- Gunicorn Documentation: https://docs.gunicorn.org/
- Nginx Documentation: https://nginx.org/en/docs/
- PostgreSQL Documentation: https://www.postgresql.org/docs/
- Let's Encrypt: https://letsencrypt.org/docs/
