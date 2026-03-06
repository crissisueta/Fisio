"""
WSGI config for fisio_project project.
"""

import os
from pathlib import Path

# load environment variables from env/Fisio.env if available
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from django.core.wsgi import get_wsgi_application

# load before settings are accessed
if load_dotenv:
    base_dir = Path(__file__).resolve().parent.parent
    env_path = base_dir / 'env' / 'Fisio.env'
    if env_path.exists():
        load_dotenv(env_path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fisio_project.settings')

application = get_wsgi_application()
