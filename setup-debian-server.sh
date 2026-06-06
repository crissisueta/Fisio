#!/bin/bash

# Fisio Django Application - Debian Server Automated Setup Script
# This script automates the setup process for deploying Fisio on Debian

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration variables
APP_USER="fisio"
APP_GROUP="www-data"
APP_DIR="/home/${APP_USER}/fisio_project"
DB_NAME="fisio_db"
DB_USER="fisio_user"

print_section() {
    echo -e "\n${GREEN}=== $1 ===${NC}\n"
}

print_error() {
    echo -e "${RED}ERROR: $1${NC}" >&2
}

print_warning() {
    echo -e "${YELLOW}WARNING: $1${NC}"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root"
        exit 1
    fi
}

# Step 1: Update system
update_system() {
    print_section "Step 1: Updating System Packages"
    apt-get update
    apt-get upgrade -y
}

# Step 2: Install dependencies
install_dependencies() {
    print_section "Step 2: Installing Dependencies"
    apt-get install -y \
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

    print_warning "Ensure PostgreSQL is running:"
    systemctl start postgresql
    systemctl enable postgresql
}

# Step 3: Create application user
create_app_user() {
    print_section "Step 3: Creating Application User"
    
    if id "${APP_USER}" &>/dev/null; then
        print_warning "User ${APP_USER} already exists"
    else
        useradd -m -s /bin/bash ${APP_USER}
        print_warning "Created user ${APP_USER}"
    fi
}

# Step 4: Setup PostgreSQL database
setup_database() {
    print_section "Step 4: Setting Up PostgreSQL Database"
    
    read -s -p "Enter PostgreSQL password for ${DB_USER}: " DB_PASSWORD
    echo
    
    sudo -u postgres psql << EOF
-- Drop existing database and user if they exist (for clean setup)
-- Uncomment the lines below if you want to reset the database
-- DROP DATABASE IF EXISTS ${DB_NAME};
-- DROP USER IF EXISTS ${DB_USER};

CREATE DATABASE IF NOT EXISTS ${DB_NAME};
DO \$\$
BEGIN
    CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';
EXCEPTION WHEN DUPLICATE_OBJECT THEN
    ALTER USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';
END
\$\$;

ALTER ROLE ${DB_USER} SET client_encoding TO 'utf8';
ALTER ROLE ${DB_USER} SET default_transaction_isolation TO 'read committed';
ALTER ROLE ${DB_USER} SET default_transaction_deferrable TO on;
ALTER ROLE ${DB_USER} SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
EOF

    print_warning "Save your PostgreSQL password for the .env file:"
    echo "DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@localhost:5432/${DB_NAME}"
}

# Step 5: Setup application directory
setup_app_directory() {
    print_section "Step 5: Setting Up Application Directory"
    
    if [ ! -d "${APP_DIR}" ]; then
        print_error "Application directory ${APP_DIR} does not exist!"
        echo "Please clone or upload your repository to ${APP_DIR}"
        exit 1
    fi
    
    chown -R ${APP_USER}:${APP_USER} ${APP_DIR}
    print_warning "Application directory ownership set to ${APP_USER}:${APP_USER}"
}

# Step 6: Setup Python virtual environment
setup_venv() {
    print_section "Step 6: Setting Up Python Virtual Environment"
    
    su - ${APP_USER} << EOF
cd ${APP_DIR}
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
EOF

    print_warning "Virtual environment created and dependencies installed"
}

# Step 7: Create .env file template
create_env_file() {
    print_section "Step 7: Creating .env File Template"
    
    if [ -f "${APP_DIR}/.env" ]; then
        print_warning ".env file already exists, skipping creation"
    else
        cat > ${APP_DIR}/.env << EOF
DEBUG=False
DJANGO_SECRET_KEY=CHANGE_ME_TO_A_RANDOM_SECRET_KEY
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=
DATABASE_URL=postgresql://${DB_USER}:YOUR_PASSWORD@localhost:5432/${DB_NAME}
EOF
        
        chown ${APP_USER}:${APP_USER} ${APP_DIR}/.env
        chmod 600 ${APP_DIR}/.env
        print_warning ".env file created at ${APP_DIR}/.env"
        print_warning "IMPORTANT: Edit .env file with your actual values"
    fi
}

# Step 8: Run Django migrations
setup_django() {
    print_section "Step 8: Setting Up Django"
    
    su - ${APP_USER} << EOF
cd ${APP_DIR}
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
EOF

    print_warning "Django migrations and static files configured"
}

# Step 9: Create systemd service for Gunicorn
create_systemd_service() {
    print_section "Step 9: Creating Systemd Service for Gunicorn"
    
    cat > /etc/systemd/system/gunicorn-fisio.service << 'EOF'
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
EOF

    systemctl daemon-reload
    systemctl enable gunicorn-fisio
    print_warning "Gunicorn systemd service created"
}

# Step 10: Configure Nginx
configure_nginx() {
    print_section "Step 10: Configuring Nginx"
    
    cat > /etc/nginx/sites-available/fisio << 'EOF'
upstream gunicorn_fisio {
    server unix:/home/fisio/fisio_project/gunicorn.sock fail_timeout=0;
}

server {
    listen 80;
    server_name _;
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
EOF

    rm -f /etc/nginx/sites-enabled/default
    ln -sf /etc/nginx/sites-available/fisio /etc/nginx/sites-enabled/fisio
    
    nginx -t && systemctl restart nginx
    print_warning "Nginx configured"
}

# Step 11: Setup firewall
setup_firewall() {
    print_section "Step 11: Setting Up Firewall"
    
    ufw enable --force
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow 22/tcp      # SSH
    ufw allow 80/tcp      # HTTP
    ufw allow 443/tcp     # HTTPS
    
    print_warning "Firewall configured"
}

# Step 12: Create backup script
create_backup_script() {
    print_section "Step 12: Creating Backup Script"
    
    cat > /usr/local/bin/backup-fisio.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Backup database
pg_dump -U fisio_user fisio_db | gzip > $BACKUP_DIR/fisio_db_$DATE.sql.gz

# Backup media files
tar -czf $BACKUP_DIR/fisio_media_$DATE.tar.gz /home/fisio/fisio_project/media/ 2>/dev/null || true

# Keep only last 30 days of backups
find $BACKUP_DIR -name "fisio_db_*.sql.gz" -mtime +30 -delete
find $BACKUP_DIR -name "fisio_media_*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
EOF

    chmod +x /usr/local/bin/backup-fisio.sh
    print_warning "Backup script created at /usr/local/bin/backup-fisio.sh"
}

# Main execution
main() {
    clear
    echo -e "${GREEN}"
    cat << "EOF"
╔════════════════════════════════════════════════════════════════╗
║     Fisio Django Application - Debian Server Setup              ║
║     Automated Installation Script                              ║
╚════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    
    check_root
    
    # Summary before starting
    echo "This script will:"
    echo "  1. Update system packages"
    echo "  2. Install PostgreSQL, Python, Nginx, and dependencies"
    echo "  3. Create application user and database"
    echo "  4. Setup Python virtual environment"
    echo "  5. Configure Gunicorn and Nginx"
    echo "  6. Setup firewall and SSL"
    echo ""
    read -p "Continue with setup? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "Setup cancelled"
        exit 1
    fi
    
    # Run setup steps
    update_system
    install_dependencies
    create_app_user
    setup_database
    setup_app_directory
    setup_venv
    create_env_file
    setup_django
    create_systemd_service
    configure_nginx
    setup_firewall
    create_backup_script
    
    # Print summary
    print_section "Setup Complete!"
    echo "Next steps:"
    echo "1. Edit .env file with your actual values:"
    echo "   nano ${APP_DIR}/.env"
    echo ""
    echo "2. Start Gunicorn service:"
    echo "   sudo systemctl start gunicorn-fisio"
    echo ""
    echo "3. Configure your domain in Nginx and setup SSL:"
    echo "   sudo certbot --nginx -d your-domain.com"
    echo ""
    echo "4. Check service status:"
    echo "   sudo systemctl status gunicorn-fisio"
    echo "   sudo systemctl status nginx"
    echo ""
    echo "5. View logs:"
    echo "   sudo journalctl -u gunicorn-fisio -f"
    echo ""
}

main "$@"
