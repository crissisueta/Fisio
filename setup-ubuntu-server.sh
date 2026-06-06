#!/usr/bin/env bash

# Fisio Django Application - Ubuntu Server Automated Setup Script
# Target: Ubuntu Server 24.04 LTS. Ubuntu does not publish a 24.02 server
# release; this script is intended for the current 24.x LTS server line.

set -Eeuo pipefail
set -f

APP_USER="${APP_USER:-fisio}"
APP_GROUP="${APP_GROUP:-www-data}"
APP_DIR="${APP_DIR:-/home/${APP_USER}/fisio_project}"
PROJECT_SOURCE="${PROJECT_SOURCE:-$(pwd)}"
REPO_URL="${REPO_URL:-}"
REPO_BRANCH="${REPO_BRANCH:-main}"

DB_NAME="${DB_NAME:-fisio_db}"
DB_USER="${DB_USER:-fisio_user}"
DB_PASSWORD="${DB_PASSWORD:-}"

DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY:-}"
ALLOWED_HOSTS="${ALLOWED_HOSTS:-}"
CSRF_TRUSTED_ORIGINS="${CSRF_TRUSTED_ORIGINS:-}"
EMAIL_BACKEND="${EMAIL_BACKEND:-django.core.mail.backends.smtp.EmailBackend}"

DOMAIN_NAMES="${DOMAIN_NAMES:-}"
ENABLE_SSL="${ENABLE_SSL:-0}"
SSL_EMAIL="${SSL_EMAIL:-}"
ENABLE_UFW="${ENABLE_UFW:-1}"
SSH_PORT="${SSH_PORT:-22}"
ENABLE_BACKUPS="${ENABLE_BACKUPS:-1}"
RUN_UPGRADE="${RUN_UPGRADE:-1}"
ASSUME_YES="${ASSUME_YES:-0}"
SKIP_APP_COPY="${SKIP_APP_COPY:-0}"

SERVICE_NAME="${SERVICE_NAME:-gunicorn-fisio}"
NGINX_SITE="${NGINX_SITE:-fisio}"
GUNICORN_WORKERS="${GUNICORN_WORKERS:-3}"

if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    NC=''
fi

print_section() {
    printf '\n%b=== %s ===%b\n\n' "${GREEN}" "$1" "${NC}"
}

print_warning() {
    printf '%bWARNING:%b %s\n' "${YELLOW}" "${NC}" "$1"
}

print_error() {
    printf '%bERROR:%b %s\n' "${RED}" "${NC}" "$1" >&2
}

die() {
    print_error "$1"
    exit 1
}

show_help() {
    cat <<'EOF'
Usage:
  sudo -E ./setup-ubuntu-server.sh [options]

Options:
  --domain "example.com www.example.com"  Configure Nginx server_name and Django hosts.
  --email admin@example.com               Email for Let's Encrypt.
  --ssl                                   Request and configure a Let's Encrypt certificate.
  --repo-url URL                          Clone/update the app from a Git repository.
  --repo-branch BRANCH                    Branch to clone/update. Default: main.
  --app-dir PATH                          Install directory. Default: /home/fisio/fisio_project.
  --project-source PATH                   Local project folder to copy when --repo-url is not used.
  --skip-copy                             Use the existing app directory as-is.
  --no-upgrade                            Skip apt-get upgrade.
  --no-ufw                                Do not enable/configure UFW.
  --no-backups                            Do not install the backup script and cron entry.
  -y, --assume-yes                        Do not ask for confirmation.
  -h, --help                              Show this help.

Common environment variables:
  DB_PASSWORD, DJANGO_SECRET_KEY, APP_USER, DB_NAME, DB_USER, SSH_PORT,
  DOMAIN_NAMES, SSL_EMAIL, ENABLE_SSL, ENABLE_UFW, ENABLE_BACKUPS.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    show_help
    exit 0
fi

if [[ $EUID -ne 0 ]]; then
    exec sudo -E bash "$0" "$@"
fi

while [[ $# -gt 0 ]]; do
    case "$1" in
        --domain|--domains)
            DOMAIN_NAMES="${2:-}"
            shift 2
            ;;
        --email)
            SSL_EMAIL="${2:-}"
            shift 2
            ;;
        --ssl)
            ENABLE_SSL=1
            shift
            ;;
        --no-ssl)
            ENABLE_SSL=0
            shift
            ;;
        --repo-url)
            REPO_URL="${2:-}"
            shift 2
            ;;
        --repo-branch)
            REPO_BRANCH="${2:-}"
            shift 2
            ;;
        --app-dir)
            APP_DIR="${2:-}"
            shift 2
            ;;
        --project-source)
            PROJECT_SOURCE="${2:-}"
            shift 2
            ;;
        --skip-copy)
            SKIP_APP_COPY=1
            shift
            ;;
        --no-upgrade)
            RUN_UPGRADE=0
            shift
            ;;
        --no-ufw)
            ENABLE_UFW=0
            shift
            ;;
        --no-backups)
            ENABLE_BACKUPS=0
            shift
            ;;
        -y|--assume-yes)
            ASSUME_YES=1
            shift
            ;;
        *)
            die "Unknown option: $1"
            ;;
    esac
done

run_as_app() {
    sudo -H -u "${APP_USER}" "$@"
}

normalize_names() {
    printf '%s' "$1" | tr ',' ' ' | xargs
}

append_csv_unique() {
    local list="$1"
    shift
    local value
    for value in "$@"; do
        [[ -z "${value}" ]] && continue
        if [[ ",${list}," != *",${value},"* ]]; then
            if [[ -z "${list}" ]]; then
                list="${value}"
            else
                list="${list},${value}"
            fi
        fi
    done
    printf '%s' "${list}"
}

read_dotenv_value() {
    local name="$1"
    local env_file="${APP_DIR}/.env"
    [[ -f "${env_file}" ]] || return 0
    grep -E "^[[:space:]]*${name}=" "${env_file}" | tail -n 1 | sed -E "s/^[^=]+=//; s/^['\"]//; s/['\"]$//"
}

generate_secret_key() {
    python3 -c 'import secrets; print(secrets.token_urlsafe(50))'
}

urlencode() {
    python3 -c 'from urllib.parse import quote; import sys; print(quote(sys.argv[1], safe=""))' "$1"
}

db_password_from_url() {
    python3 -c 'from urllib.parse import unquote, urlparse; import sys; print(unquote(urlparse(sys.argv[1]).password or ""))' "$1"
}

sql_literal() {
    printf '%s' "$1" | sed "s/'/''/g"
}

validate_config() {
    [[ "${APP_USER}" =~ ^[a-z_][a-z0-9_-]*$ ]] || die "APP_USER must be a valid Linux username."
    [[ "${DB_NAME}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || die "DB_NAME must be a PostgreSQL identifier."
    [[ "${DB_USER}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || die "DB_USER must be a PostgreSQL identifier."
    [[ "${APP_DIR}" != *" "* ]] || die "APP_DIR cannot contain spaces because systemd/nginx paths are generated from it."
    [[ "${SSH_PORT}" =~ ^[0-9]+$ ]] || die "SSH_PORT must be numeric."

    if [[ "${ENABLE_SSL}" == "1" ]]; then
        [[ -n "${DOMAIN_NAMES}" ]] || die "--ssl requires --domain."
        [[ -n "${SSL_EMAIL}" ]] || die "--ssl requires --email."
    fi
}

check_ubuntu() {
    print_section "Checking Operating System"
    if [[ -r /etc/os-release ]]; then
        # shellcheck disable=SC1091
        . /etc/os-release
        if [[ "${ID:-}" != "ubuntu" ]]; then
            print_warning "This script is written for Ubuntu 24.x, but detected ${PRETTY_NAME:-unknown OS}."
        elif [[ "${VERSION_ID:-}" != 24.* ]]; then
            print_warning "This script targets Ubuntu 24.x, but detected ${PRETTY_NAME:-Ubuntu}."
        else
            printf 'Detected %s\n' "${PRETTY_NAME:-Ubuntu}"
        fi
    else
        print_warning "Could not read /etc/os-release."
    fi
}

confirm_before_start() {
    [[ "${ASSUME_YES}" == "1" || ! -t 0 ]] && return 0

    cat <<EOF
This will install and configure Fisio with:
  App user:       ${APP_USER}
  App directory:  ${APP_DIR}
  Database:       ${DB_NAME}
  Database user:  ${DB_USER}
  Nginx site:     ${NGINX_SITE}
  Gunicorn unit:  ${SERVICE_NAME}
  Domains:        ${DOMAIN_NAMES:-none}
  SSL:            ${ENABLE_SSL}
  UFW enabled:    ${ENABLE_UFW}

EOF
    read -r -p "Continue? [y/N] " reply
    [[ "${reply}" =~ ^[Yy]$ ]] || die "Setup cancelled."
}

install_dependencies() {
    print_section "Installing System Packages"
    apt-get update
    if [[ "${RUN_UPGRADE}" == "1" ]]; then
        DEBIAN_FRONTEND=noninteractive apt-get upgrade -y
    fi

    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        build-essential \
        ca-certificates \
        certbot \
        curl \
        git \
        libpq-dev \
        nano \
        nginx \
        openssl \
        postgresql \
        postgresql-contrib \
        python3-certbot-nginx \
        python3-dev \
        python3-pip \
        python3-venv \
        rsync \
        sudo \
        supervisor \
        ufw \
        wget

    systemctl enable --now postgresql
}

create_app_user() {
    print_section "Creating Application User"
    if id "${APP_USER}" >/dev/null 2>&1; then
        printf 'User %s already exists.\n' "${APP_USER}"
    else
        useradd -m -s /bin/bash "${APP_USER}"
        printf 'Created user %s.\n' "${APP_USER}"
    fi
}

deploy_project() {
    print_section "Deploying Application Files"
    install -d -o "${APP_USER}" -g "${APP_USER}" "${APP_DIR}"

    local source_path app_path

    if [[ "${SKIP_APP_COPY}" == "1" ]]; then
        [[ -f "${APP_DIR}/manage.py" ]] || die "SKIP_APP_COPY is set, but ${APP_DIR}/manage.py does not exist."
        printf 'Using existing application directory: %s\n' "${APP_DIR}"
    elif [[ -n "${REPO_URL}" ]]; then
        if [[ -d "${APP_DIR}/.git" ]]; then
            run_as_app git -C "${APP_DIR}" fetch --all --prune
            run_as_app git -C "${APP_DIR}" checkout "${REPO_BRANCH}"
            run_as_app git -C "${APP_DIR}" pull --ff-only origin "${REPO_BRANCH}"
        elif [[ -n "$(find "${APP_DIR}" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
            die "${APP_DIR} exists and is not empty. Use --skip-copy or choose another --app-dir."
        else
            run_as_app git clone --branch "${REPO_BRANCH}" "${REPO_URL}" "${APP_DIR}"
        fi
    else
        [[ -f "${PROJECT_SOURCE}/manage.py" ]] || die "Could not find manage.py in ${PROJECT_SOURCE}. Run from the project root or use --project-source."
        source_path="$(realpath -m "${PROJECT_SOURCE}")"
        app_path="$(realpath -m "${APP_DIR}")"

        if [[ "${source_path}" == "${app_path}" ]]; then
            printf 'Project source is already the app directory: %s\n' "${APP_DIR}"
        else
            rsync -a --delete \
                --exclude='.git/' \
                --exclude='.agents/' \
                --exclude='.codex' \
                --include='.env.example' \
                --exclude='.env' \
                --exclude='.env.*' \
                --exclude='env/' \
                --exclude='venv/' \
                --exclude='.venv/' \
                --exclude='db.sqlite3' \
                --exclude='media/' \
                --exclude='staticfiles/' \
                --exclude='__pycache__/' \
                --exclude='*.pyc' \
                --exclude='.pytest_cache/' \
                --exclude='.coverage' \
                --exclude='htmlcov/' \
                "${PROJECT_SOURCE}/" "${APP_DIR}/"
        fi
    fi

    install -d -o "${APP_USER}" -g "${APP_USER}" "${APP_DIR}/media" "${APP_DIR}/staticfiles"
    chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"
    chmod 755 "/home/${APP_USER}" "${APP_DIR}"
}

load_existing_env_defaults() {
    print_section "Preparing Environment Values"

    local existing_secret existing_allowed_hosts existing_csrf existing_db_url existing_db_password
    existing_secret="$(read_dotenv_value DJANGO_SECRET_KEY || true)"
    existing_allowed_hosts="$(read_dotenv_value ALLOWED_HOSTS || true)"
    existing_csrf="$(read_dotenv_value CSRF_TRUSTED_ORIGINS || true)"
    existing_db_url="$(read_dotenv_value DATABASE_URL || true)"

    if [[ -z "${DJANGO_SECRET_KEY}" && -n "${existing_secret}" ]]; then
        DJANGO_SECRET_KEY="${existing_secret}"
    fi

    if [[ -z "${DB_PASSWORD}" && "${existing_db_url}" == postgresql* ]]; then
        existing_db_password="$(db_password_from_url "${existing_db_url}")"
        if [[ -n "${existing_db_password}" ]]; then
            DB_PASSWORD="${existing_db_password}"
        fi
    fi

    if [[ -z "${DJANGO_SECRET_KEY}" ]]; then
        DJANGO_SECRET_KEY="$(generate_secret_key)"
    fi

    if [[ -z "${DB_PASSWORD}" ]]; then
        DB_PASSWORD="$(openssl rand -hex 24)"
    fi

    local server_names host_ip domain origins
    server_names="$(normalize_names "${DOMAIN_NAMES}")"
    DOMAIN_NAMES="${server_names}"

    if [[ -z "${ALLOWED_HOSTS}" && -n "${existing_allowed_hosts}" && -z "${DOMAIN_NAMES}" ]]; then
        ALLOWED_HOSTS="${existing_allowed_hosts}"
    fi

    if [[ -z "${ALLOWED_HOSTS}" ]]; then
        ALLOWED_HOSTS="127.0.0.1,localhost"
        host_ip="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
        for domain in ${DOMAIN_NAMES}; do
            ALLOWED_HOSTS="$(append_csv_unique "${ALLOWED_HOSTS}" "${domain}")"
        done
        ALLOWED_HOSTS="$(append_csv_unique "${ALLOWED_HOSTS}" "${host_ip}")"
    fi

    if [[ -z "${CSRF_TRUSTED_ORIGINS}" && -n "${existing_csrf}" && -z "${DOMAIN_NAMES}" ]]; then
        CSRF_TRUSTED_ORIGINS="${existing_csrf}"
    fi

    if [[ -z "${CSRF_TRUSTED_ORIGINS}" && -n "${DOMAIN_NAMES}" ]]; then
        origins=""
        for domain in ${DOMAIN_NAMES}; do
            origins="$(append_csv_unique "${origins}" "https://${domain}" "http://${domain}")"
        done
        CSRF_TRUSTED_ORIGINS="${origins}"
    fi
}

setup_database() {
    print_section "Configuring PostgreSQL"

    local db_password_sql database_exists
    db_password_sql="$(sql_literal "${DB_PASSWORD}")"

    sudo -u postgres psql -v ON_ERROR_STOP=1 <<EOF
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${DB_USER}') THEN
        CREATE ROLE ${DB_USER} LOGIN PASSWORD '${db_password_sql}';
    ELSE
        ALTER ROLE ${DB_USER} WITH PASSWORD '${db_password_sql}';
    END IF;
END
\$\$;

ALTER ROLE ${DB_USER} SET client_encoding TO 'utf8';
ALTER ROLE ${DB_USER} SET default_transaction_isolation TO 'read committed';
ALTER ROLE ${DB_USER} SET default_transaction_deferrable TO on;
ALTER ROLE ${DB_USER} SET timezone TO 'UTC';
EOF

    database_exists="$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" || true)"
    if [[ "${database_exists}" != "1" ]]; then
        sudo -u postgres createdb --owner="${DB_USER}" "${DB_NAME}"
    fi

    sudo -u postgres psql -v ON_ERROR_STOP=1 -d "${DB_NAME}" <<EOF
ALTER DATABASE ${DB_NAME} OWNER TO ${DB_USER};
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
GRANT ALL ON SCHEMA public TO ${DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${DB_USER};
EOF
}

write_env_file() {
    print_section "Writing Django .env"

    local encoded_db_password env_file timestamp
    encoded_db_password="$(urlencode "${DB_PASSWORD}")"
    env_file="${APP_DIR}/.env"

    if [[ -f "${env_file}" ]]; then
        timestamp="$(date +%Y%m%d_%H%M%S)"
        cp "${env_file}" "${env_file}.bak.${timestamp}"
        chown "${APP_USER}:${APP_USER}" "${env_file}.bak.${timestamp}"
        chmod 600 "${env_file}.bak.${timestamp}"
    fi

    cat > "${env_file}" <<EOF
DEBUG=False
DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
ALLOWED_HOSTS=${ALLOWED_HOSTS}
CSRF_TRUSTED_ORIGINS=${CSRF_TRUSTED_ORIGINS}
DATABASE_URL=postgresql://${DB_USER}:${encoded_db_password}@localhost:5432/${DB_NAME}
EMAIL_BACKEND=${EMAIL_BACKEND}
EOF

    chown "${APP_USER}:${APP_USER}" "${env_file}"
    chmod 600 "${env_file}"
}

setup_python_and_django() {
    print_section "Installing Python Dependencies"
    run_as_app python3 -m venv "${APP_DIR}/venv"
    run_as_app "${APP_DIR}/venv/bin/python" -m pip install --upgrade pip setuptools wheel
    run_as_app "${APP_DIR}/venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

    print_section "Running Django Setup"
    run_as_app bash -c 'cd "$1" && "$1/venv/bin/python" manage.py check' _ "${APP_DIR}"
    run_as_app bash -c 'cd "$1" && "$1/venv/bin/python" manage.py migrate' _ "${APP_DIR}"
    run_as_app bash -c 'cd "$1" && "$1/venv/bin/python" manage.py collectstatic --noinput' _ "${APP_DIR}"
}

create_systemd_service() {
    print_section "Configuring Gunicorn Service"

    cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=Gunicorn application server for Fisio
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=${APP_USER}
Group=${APP_GROUP}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
UMask=0007
ExecStart=${APP_DIR}/venv/bin/gunicorn \\
    --workers ${GUNICORN_WORKERS} \\
    --worker-class sync \\
    --bind unix:${APP_DIR}/gunicorn.sock \\
    fisio_project.wsgi:application
Restart=always
RestartSec=5
PrivateTmp=true
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable "${SERVICE_NAME}"
    systemctl restart "${SERVICE_NAME}"
}

configure_nginx() {
    print_section "Configuring Nginx"

    local server_names
    server_names="${DOMAIN_NAMES:-_}"

    cat > "/etc/nginx/sites-available/${NGINX_SITE}" <<EOF
upstream gunicorn_fisio {
    server unix:${APP_DIR}/gunicorn.sock fail_timeout=0;
}

server {
    listen 80;
    server_name ${server_names};
    client_max_body_size 20M;

    location /static/ {
        alias ${APP_DIR}/staticfiles/;
        expires 30d;
    }

    location /media/ {
        alias ${APP_DIR}/media/;
        expires 7d;
    }

    location / {
        proxy_pass http://gunicorn_fisio;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
        proxy_read_timeout 60s;
        proxy_connect_timeout 60s;
    }
}
EOF

    rm -f /etc/nginx/sites-enabled/default
    ln -sf "/etc/nginx/sites-available/${NGINX_SITE}" "/etc/nginx/sites-enabled/${NGINX_SITE}"
    nginx -t
    systemctl enable nginx
    systemctl restart nginx
}

setup_ssl() {
    [[ "${ENABLE_SSL}" == "1" ]] || return 0

    print_section "Configuring Let's Encrypt SSL"
    local certbot_args domain
    certbot_args=(--nginx --non-interactive --agree-tos --redirect -m "${SSL_EMAIL}")
    for domain in ${DOMAIN_NAMES}; do
        certbot_args+=(-d "${domain}")
    done

    certbot "${certbot_args[@]}"
    systemctl enable --now certbot.timer
}

setup_firewall() {
    [[ "${ENABLE_UFW}" == "1" ]] || return 0

    print_section "Configuring Firewall"
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow "${SSH_PORT}/tcp"
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw --force enable
}

create_backup_script() {
    [[ "${ENABLE_BACKUPS}" == "1" ]] || return 0

    print_section "Creating Backup Script"
    cat > /usr/local/bin/backup-fisio.sh <<EOF
#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="/home/backups/fisio"
APP_DIR="${APP_DIR}"
DB_NAME="${DB_NAME}"
DATE="\$(date +%Y%m%d_%H%M%S)"

mkdir -p "\${BACKUP_DIR}"

sudo -u postgres pg_dump "\${DB_NAME}" | gzip > "\${BACKUP_DIR}/fisio_db_\${DATE}.sql.gz"

if [[ -d "\${APP_DIR}/media" ]]; then
    tar -czf "\${BACKUP_DIR}/fisio_media_\${DATE}.tar.gz" -C "\${APP_DIR}" media
fi

find "\${BACKUP_DIR}" -name 'fisio_db_*.sql.gz' -mtime +30 -delete
find "\${BACKUP_DIR}" -name 'fisio_media_*.tar.gz' -mtime +30 -delete

echo "Backup completed: \${DATE}"
EOF

    chmod +x /usr/local/bin/backup-fisio.sh

    cat > /etc/cron.d/fisio-backup <<'EOF'
0 2 * * * root /usr/local/bin/backup-fisio.sh >> /var/log/fisio-backup.log 2>&1
EOF
}

print_summary() {
    print_section "Setup Complete"
    cat <<EOF
Fisio is installed at:
  ${APP_DIR}

Generated credentials and Django environment are stored in:
  ${APP_DIR}/.env

Useful commands:
  sudo systemctl status ${SERVICE_NAME}
  sudo systemctl status nginx
  sudo journalctl -u ${SERVICE_NAME} -f
  sudo tail -f /var/log/nginx/error.log

Create a Django admin user:
  sudo -u ${APP_USER} -H bash -lc 'cd ${APP_DIR} && source venv/bin/activate && python manage.py createsuperuser'

Update the app later:
  sudo -u ${APP_USER} -H git -C ${APP_DIR} pull --ff-only
  sudo -u ${APP_USER} -H ${APP_DIR}/venv/bin/pip install -r ${APP_DIR}/requirements.txt
  sudo -u ${APP_USER} -H bash -lc 'cd ${APP_DIR} && ${APP_DIR}/venv/bin/python manage.py migrate && ${APP_DIR}/venv/bin/python manage.py collectstatic --noinput'
  sudo systemctl restart ${SERVICE_NAME}
EOF
}

main() {
    validate_config
    check_ubuntu
    confirm_before_start
    install_dependencies
    create_app_user
    deploy_project
    load_existing_env_defaults
    setup_database
    write_env_file
    setup_python_and_django
    create_systemd_service
    configure_nginx
    setup_firewall
    setup_ssl
    create_backup_script
    print_summary
}

main "$@"
