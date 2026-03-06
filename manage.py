#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path

# load local environment variables from env/Fisio.env when present
# this lets developers run the project locally without editing settings.py
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None



def main():
    """Run administrative tasks."""
    # if a .env file exists in the env directory, load it before Django settings
    if load_dotenv:
        base_dir = Path(__file__).resolve().parent
        env_path = base_dir / 'env' / 'Fisio.env'
        if env_path.exists():
            load_dotenv(env_path)

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fisio_project.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
