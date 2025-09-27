import os
import sys
import re

# Конфигурация сред Go. Порядок важен: taskfile -> mage -> make -> pure

go_environments = {
    "taskfile": {
        "manifests": ["Taskfile.yml", "Taskfile.yaml"],
        "setup_commands": [
            'echo "-> Обнаружен taskfile. Установка go-task..."',
            'go install github.com/go-task/task/v3/cmd/task@v3.36.0',
            'go mod download 2>/dev/null || true',
        ],
        "run_cmd": "task start",  # по умолчанию
    },
    "mage": {
        "manifests": ["magefile.go"],
        "setup_commands": [
            'echo "-> Обнаружен magefile. Установка mage..."',
            'go install github.com/magefile/mage@latest',
            'go mod download 2>/dev/null || true',
        ],
        "run_cmd": "mage run",
    },
    "make": {
        "manifests": ["Makefile"],
        "setup_commands": [
            'echo "-> Обнаружен Makefile. Установка make..."',
            'apk add --no-cache make',
            'go mod download 2>/dev/null || true',
            # Добавлена статическая сборка перед запуском (на случай, если makefile не содержит build)
            # Если уверены, что make run соберет, эту строку можно удалить.
            'CGO_ENABLED=0 make build',
        ],
        # Предполагаем, что make run запускает приложение
        "run_cmd": "make run",
    },
    "pure": {
        "manifests": ["go.mod", "main.go"],
        "setup_commands": [
            'echo "-> Обнаружен чистый Go проект."',
            'go mod download 2>/dev/null || true',
        ],
        "run_cmd": "go run .",
    }
}
def extract_go_version(path: str) -> str:
    default_version = "1.21"
    gomod_path = os.path.join(path, "go.mod")
    if os.path.exists(gomod_path):
        try:
            with open(gomod_path, "r", encoding="utf-8") as f:
                content = f.read()
            go_match = re.search(r'go\s+(\d+\.\d+)', content)
            if go_match:
                return go_match.group(1)
        except Exception as e:
            print(f"Предупреждение: не удалось парсить go.mod: {e}")

    go_version_path = os.path.join(path, ".go-version")
    if os.path.exists(go_version_path):
        try:
            with open(go_version_path, "r", encoding="utf-8") as f:
                version = f.read().strip()
                version_match = re.search(r'(\d+\.\d+)', version)
                if version_match:
                    return version_match.group(1)
        except Exception as e:
            print(f"Предупреждение: не удалось прочитать .go-version: {e}")

    print(f"Версия Go не найдена в манифестах, используется дефолтная: {default_version}")
    return default_version

def get_docker_image(go_version: str) -> str:
    return f"golang:{go_version}-alpine"
def detect_taskfile_run_cmd(path: str) -> str:
    taskfile_path = None
    for name in ["Taskfile.yml", "Taskfile.yaml"]:
        candidate = os.path.join(path, name)
        if os.path.exists(candidate):
            taskfile_path = candidate
            break
    if not taskfile_path:
        return "go run ."

    tasks = []
    try:
        with open(taskfile_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        in_tasks_section = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("tasks:"):
                in_tasks_section = True
                continue
            if in_tasks_section:
                if stripped and not stripped.startswith("#") and not stripped.startswith("-") and ":" in stripped:
                    task_name = stripped.split(":")[0].strip()
                    tasks.append(task_name)

        if "start" in tasks:
            return "task start"
        elif tasks:
            first_task = tasks[0]
            # Если это сборка — явно запускаем бинарь
            if "build" in first_task.lower():
                return f"task {first_task} && ./app"
            else:
                return f"task {first_task}"
    except Exception as e:
        print(f"Предупреждение: не удалось прочитать {taskfile_path}: {e}")

    return "go run ."

def parse_image_and_create_bash(path: str) -> str:
    print("Парсим докер образ из структуры проекта (Go)...")

    environment = "pure"
    env_config = go_environments["pure"]

    # Определяем среду сборки
    for key, config in go_environments.items():
        if key == "pure":
            continue
        for manifest in config["manifests"]:
            if os.path.exists(os.path.join(path, manifest)):
                environment = key
                env_config = config
                break
        if environment != "pure":
            break

    if environment == "taskfile":
        env_config["run_cmd"] = detect_taskfile_run_cmd(path)

    go_version = extract_go_version(path)
    docker_image = get_docker_image(go_version)

    print(f"Обнаружен тип сборки: {environment}")
    print(f"Версия Go: {go_version}")
    print(f"Docker образ: {docker_image}")

    run_sh_content = f"""#!/bin/sh
# Автоматически сгенерированный скрипт запуска для проекта Go

set -e

echo "--- Настройка среды и загрузка модулей ---"
{"\n".join(env_config["setup_commands"])}

echo "--- Запуск приложения ({environment}) ---"
exec {env_config["run_cmd"]}
"""

    run_sh_path = os.path.join(path, "run.sh")
    try:
        with open(run_sh_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(run_sh_content)
        os.chmod(run_sh_path, 0o755)

        print(f"\nФайл run.sh для '{environment}' успешно создан в {run_sh_path}")
        print(f"Команда запуска: {env_config['run_cmd']}")
        return docker_image

    except IOError as e:
        print(f"ОШИБКА записи run.sh: {e}")
        sys.exit(1)
