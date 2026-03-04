#!/usr/bin/env python
"""
Setup script for Django Fisioterapia application
Installs dependencies and initializes the database
"""

import os
import sys
import subprocess
import platform

def run_command(command, description):
    """Run a shell command and report status"""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    try:
        subprocess.run(command, shell=True, check=True)
        print(f"{description} - OK")
        return True
    except subprocess.CalledProcessError as e:
        print(f"{description} - ERRO")
        print(f"Erro: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("SETUP - Sistema de Gestão de Fichas de Fisioterapia")
    print("="*60)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("ERROR: Python 3.8+ é necessário")
        sys.exit(1)
    
    print(f"Python {sys.version.split()[0]} detectado")
    
    # Detect OS for appropriate commands
    is_windows = platform.system() == "Windows"
    venv_cmd = "venv\\Scripts\\activate" if is_windows else "source venv/bin/activate"
    
    # Step 1: Create virtual environment
    if not os.path.exists("venv"):
        if not run_command(f"{sys.executable} -m venv venv", "Criando ambiente virtual"):
            sys.exit(1)
    else:
        print("\n Ambiente virtual já existe")
    
    # Step 2: Determine pip command
    if is_windows:
        pip_cmd = "venv\\Scripts\\pip"
    else:
        pip_cmd = "venv/bin/pip"
    
    # Step 3: Install requirements
    if not run_command(f"{pip_cmd} install -r requirements.txt", "Instalando dependências"):
        sys.exit(1)
    
    # Step 4: Run migrations
    if is_windows:
        python_cmd = "venv\\Scripts\\python"
    else:
        python_cmd = "venv/bin/python"
    
    if not run_command(f"{python_cmd} manage.py migrate", "Executando migrações"):
        sys.exit(1)
    
    # Step 5: Collect static files
    if not run_command(f"{python_cmd} manage.py collectstatic --noinput", "Coletando arquivos estáticos"):
        print("Aviso: Coleta de arquivos estáticos teve um aviso (isso é normal)")
    
    print("\n" + "="*60)
    print("SETUP CONCLUÍDO COM SUCESSO!")
    print("="*60)
    print("\nPróximos passos:\n")
    
    if is_windows:
        print("1. Ativar ambiente virtual:")
        print("   venv\\Scripts\\activate")
    else:
        print("1. Ativar ambiente virtual:")
        print("   source venv/bin/activate")
    
    print("\n2. Criar usuário admin (superuser):")
    print(f"   {python_cmd} manage.py createsuperuser")
    
    print("\n3. Iniciar servidor:")
    print(f"   {python_cmd} manage.py runserver")
    
    print("\n4. Acessar a aplicação:")
    print("   http://localhost:8000")
    
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    main()
