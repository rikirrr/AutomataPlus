import os
import sys
import re

python_environments = {
    "poetry": {
        "manifest": "pyproject.toml",
        "install_cmd": "poetry install --no-root",
    },
    "conda": {
        "manifest": "environment.yml",
        "image": "continuumio/miniconda3",
        "install_cmd": "conda env create -f environment.yml",
    },
    "pip": {
        "manifest": "requirements.txt",
        "install_cmd": "pip install --no-cache-dir -r requirements.txt",
    }
}


def extract_python_version(path: str, environment: str) -> str:
    """
    Извлекает версию Python из файлов проекта.
    Возвращает версию в формате '3.12' или дефолтную '3.12'.
    """
    default_version = "3.12"

    if environment == "poetry":
        pyproject_path = os.path.join(path, "pyproject.toml")
        if os.path.exists(pyproject_path):
            try:
                with open(pyproject_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Ищем версию Python в [tool.poetry.dependencies]
                # Ищем строку python = "^3.11" или подобную
                python_match = re.search(r'python\s*=\s*["\'][\^~>=<]*(\d+\.\d+)', content)
                if python_match:
                    return python_match.group(1)

            except Exception as e:
                print(f"Предупреждение: не удалось парсить pyproject.toml: {e}")

    elif environment == "pip":
        # Ищем в requirements.txt строки типа "python>=3.11"
        requirements_path = os.path.join(path, "requirements.txt")
        if os.path.exists(requirements_path):
            try:
                with open(requirements_path, "r", encoding="utf-8") as f:
                    content = f.read()

                python_match = re.search(r'python[>=<~!]*(\d+\.\d+)', content, re.IGNORECASE)
                if python_match:
                    return python_match.group(1)

            except Exception as e:
                print(f"Предупреждение: не удалось прочитать requirements.txt: {e}")

    # Проверяем .python-version файл (используется pyenv)
    python_version_path = os.path.join(path, ".python-version")
    if os.path.exists(python_version_path):
        try:
            with open(python_version_path, "r", encoding="utf-8") as f:
                version = f.read().strip()
                # Извлекаем основную версию (3.11.5 -> 3.11)
                version_match = re.search(r'(\d+\.\d+)', version)
                if version_match:
                    return version_match.group(1)
        except Exception as e:
            print(f"Предупреждение: не удалось прочитать .python-version: {e}")

    # Проверяем runtime.txt (используется Heroku и другими)
    runtime_path = os.path.join(path, "runtime.txt")
    if os.path.exists(runtime_path):
        try:
            with open(runtime_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                # Ищем строки типа "python-3.11.5"
                version_match = re.search(r'python-(\d+\.\d+)', content)
                if version_match:
                    return version_match.group(1)
        except Exception as e:
            print(f"Предупреждение: не удалось прочитать runtime.txt: {e}")

    print(f"Версия Python не найдена, используется дефолтная: {default_version}")
    return default_version


def get_docker_image(environment: str, python_version: str) -> str:
    """
    Возвращает подходящий Docker образ для среды и версии Python.
    """
    # Для всех сред используем базовый Python образ
    # Poetry и Conda устанавливаются в run.sh
    return f"python:{python_version}-slim"


def has_dependency(path: str, dep: str) -> bool:
    """
    Проверяет наличие зависимости dep в requirements.txt или pyproject.toml.
    """
    for manifest in ["requirements.txt", "pyproject.toml"]:
        manifest_path = os.path.join(path, manifest)
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                    if dep.lower() in content:
                        return True
            except Exception as e:
                print(f"Предупреждение: не удалось прочитать {manifest}: {e}")
    return False


def parse_image_and_create_bash(path: str) -> str:
    """
    Парсит структуру проекта Python для определения среды (pip, poetry, conda)
    и генерирует скрипт запуска run.sh. Возвращает имя базового образа.
    """
    print("Парсим докер образ из структуры проекта (Python)...")

    environment = None
    env_config = None

    # Определяем среду управления зависимостями
    for key, config in python_environments.items():
        if os.path.exists(os.path.join(path, config["manifest"])):
            environment = key
            env_config = config
            break

    if environment is None:
        environment = "pure"
        env_config = {"install_cmd": ""}

    # Определяем версию Python
    python_version = extract_python_version(path, environment)
    docker_image = get_docker_image(environment, python_version)

    print(f"Обнаружена среда: {environment}")
    print(f"Версия Python: {python_version}")
    print(f"Docker образ: {docker_image}")

    # Определение команды запуска
    if has_dependency(path, "gunicorn"):
        run_command = "gunicorn project_name.wsgi:application -b 0.0.0.0:8000"
    elif has_dependency(path, "uvicorn"):
        run_command = "uvicorn app:app --host 0.0.0.0 --port 8000"
    elif os.path.exists(os.path.join(path, "manage.py")):
        run_command = "python manage.py runserver 0.0.0.0:8000"
    elif os.path.exists(os.path.join(path, "app.py")):
        run_command = "python app.py"
    elif os.path.exists(os.path.join(path, "main.py")):
        run_command = "python main.py"
    else:
        run_command = "python main.py"

    # Генерируем содержимое run.sh в зависимости от среды
    if environment == "poetry":
        run_sh_content = f"""#!/bin/bash
set -e

# Установка Poetry
pip install --no-cache-dir poetry

# Настройка Poetry для работы в контейнере
poetry config virtualenvs.create false
poetry config virtualenvs.in-project false

# Очистка возможных виртуальных окружений
rm -rf .venv

# Установка зависимостей
{env_config["install_cmd"]}

# Запуск приложения
exec {run_command}
"""
    elif environment == "conda":
        run_sh_content = f"""#!/bin/bash
set -e

# Проверяем наличие conda
if ! command -v conda &> /dev/null; then
    echo "Устанавливаем miniconda..."

    # Скачиваем и устанавливаем miniconda
    wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh
    bash /tmp/miniconda.sh -b -p /opt/miniconda
    rm /tmp/miniconda.sh

    # Добавляем conda в PATH
    export PATH="/opt/miniconda/bin:$PATH"

    # Инициализация conda для bash
    /opt/miniconda/bin/conda init bash
    source ~/.bashrc
fi

# Убеждаемся что conda в PATH
export PATH="/opt/miniconda/bin:$PATH"

# Создание окружения из environment.yml
echo "Создаем conda окружение..."
{env_config["install_cmd"]}

# Получение имени окружения из environment.yml
ENV_NAME=$(grep '^name:' environment.yml | cut -d' ' -f2)

# Активация окружения
source /opt/miniconda/etc/profile.d/conda.sh
conda activate $ENV_NAME

# Запуск приложения
exec {run_command}
"""
    elif environment == "pip":
        run_sh_content = f"""#!/bin/bash
set -e
{env_config["install_cmd"]}
exec {run_command}
"""
    else:  # pure
        run_sh_content = f"""#!/bin/bash
set -e
exec {run_command}
"""

    run_sh_path = os.path.join(path, "run.sh")

    try:
        with open(run_sh_path, 'w', encoding='utf-8') as f:
            f.write(run_sh_content)

        os.chmod(run_sh_path, 0o755)

        print(f"Файл run.sh для среды '{environment}' успешно создан в {run_sh_path}")

        return docker_image

    except IOError as e:
        print(f"ОШИБКА записи run.sh: {e}")
        sys.exit(1)