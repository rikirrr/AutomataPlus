import os
import shutil
import subprocess
import sys


# Карта сред Python для определения базового образа и команды установки.
python_environments = {
    "poetry": {
        "manifest": "pyproject.toml",
        "image": "acidrain/python-poetry:latest",
        "install_cmd": "poetry install --no-root",
    },
    "conda": {
        "manifest": "environment.yml",
        "image": "continuumio/miniconda3",
        "install_cmd": "conda env create -f environment.yml",
    },
    "pip": {
        "manifest": "requirements.txt",
        "image": "python:3.12-slim",
        "install_cmd": "pip install --no-cache-dir -r requirements.txt",
    }
}

def parse_image_and_create_bash(path: str) -> str:
    """
    Парсит структуру проекта Python для определения среды (pip, poetry, conda)
    и генерирует скрипт запуска run.sh. Возвращает имя базового образа.
    """
    print("Парсим докер образ из структуры проекта (Python)...")

    # 1. Поиск файлов манифестов в корне проекта в порядке приоритета
    environment = None
    env_config = None

    # Проверяем в порядке приоритета: Poetry -> Conda -> Pip
    for key, config in python_environments.items():
        if os.path.exists(os.path.join(path, config["manifest"])):
            environment = key
            env_config = config
            break

    if environment is None:
        # Если ничего не найдено, предполагаем чистый Python
        environment = "pure"
        env_config = {
            "image": "python:3.12-slim",
            "install_cmd": "# Нет файла манифеста зависимостей (requirements.txt, pyproject.toml и т.п.)",
        }

    # 2. Определение команды запуска (Application Entry Point)
    run_command = ""

    # NOTE: Это очень упрощенная логика автоопределения сервера.
    # В реальной жизни требуется парсинг содержимого файлов или Dockerfile.

    if os.path.exists(os.path.join(path, "manage.py")):
        # Пример для Django/консольных команд через manage.py
        run_command = "# Запуск Django: gunicorn <project_name>.wsgi:application -b 0.0.0.0:8000"

    elif os.path.exists(os.path.join(path, "app.py")):
        # Пример для Flask/FastAPI
        run_command = "# Запуск ASGI/WSGI: uvicorn app:app --host 0.0.0.0 --port 8000"

    elif os.path.exists(os.path.join(path, "main.py")):
        # Консольное/обычное приложение
        run_command = "python main.py"

    else:
        run_command = "# Замените на команду для запуска вашего приложения (например, python main.py)"

    # 3. Генерация содержимого run.sh

    run_sh_content = f"""#!/bin/bash
# run.sh - Скрипт установки зависимостей и запуска проекта.
# Определенная среда: {environment.upper()}

echo "--- Настройка зависимостей ---"

# Команда установки для {environment}:
{env_config["install_cmd"]}

echo "--- Запуск приложения ---"

# Команда запуска (может потребовать ручной корректировки):
{run_command}
"""

    # 4. Запись run.sh в корень проекта
    run_sh_path = os.path.join(path, "run.sh")

    try:
        with open(run_sh_path, 'w', encoding='utf-8') as f:
            f.write(run_sh_content)

        # Делаем файл исполняемым
        os.chmod(run_sh_path, 0o755)

        print(f"Файл run.sh для среды '{environment}' успешно создан в {run_sh_path}")
        print(f"Базовый образ Docker: {env_config['image']}")

        return env_config["image"]  # Возвращаем имя базового образа

    except IOError as e:
        print(f"ОШИБКА записи run.sh: {e}")
        sys.exit(1)
