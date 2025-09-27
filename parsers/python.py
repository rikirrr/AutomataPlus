import os
import sys

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

def has_dependency(path: str, dep: str) -> bool:
    """
    Проверяет наличие зависимости dep в requirements.txt или pyproject.toml.
    """
    for manifest in ["requirements.txt", "pyproject.toml"]:
        manifest_path = os.path.join(path, manifest)
        if os.path.exists(manifest_path):
            with open(manifest_path, "r", encoding="utf-8") as f:
                content = f.read().lower()
                if dep.lower() in content:
                    return True
    return False


def parse_image_and_create_bash(path: str) -> str:
    """
    Парсит структуру проекта Python для определения среды (pip, poetry, conda)
    и генерирует скрипт запуска run.sh. Возвращает имя базового образа.
    """
    print("Парсим докер образ из структуры проекта (Python)...")

    # Поиск файлов манифестов в корне проекта в порядке приоритета
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

    # Определение команды запуска (Application Entry Point)
    run_command = ""

    # Проверяем, не подключены ли gunicorn/uvicorn
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

    # Генерация содержимого run.sh
    run_sh_content = f"""#!/bin/bash
{env_config["install_cmd"]}
{run_command}
"""

    run_sh_path = os.path.join(path, "run.sh")

    try:
        with open(run_sh_path, 'w', encoding='utf-8') as f:
            f.write(run_sh_content)

        os.chmod(run_sh_path, 0o755)

        print(f"Файл run.sh для среды '{environment}' успешно создан в {run_sh_path}")
        print(f"Базовый образ Docker: {env_config['image']}")

        return env_config["image"]

    except IOError as e:
        print(f"ОШИБКА записи run.sh: {e}")
        sys.exit(1)
