import subprocess
import sys
import uuid
import parser as p

def start_docker(lang: str, path: str):
    # Создаём Dockerfile и bash
    p.create_docker_image_and_bash(lang, path)

    # Генерируем случайное имя контейнера
    container_name = f"{lang}_{uuid.uuid4().hex[:8]}"

    print(f"[ИНФО] Случайное имя контейнера: {container_name}")

    try:
        # Собираем образ
        subprocess.run(
            ["docker", "build", "-t", container_name, path],
            check=True
        )

        # Запускаем контейнер
        subprocess.run(
            ["docker", "run", "--name", container_name, container_name],
            check=True
        )

        print(f"[OK] Контейнер {container_name} успешно запущен.")
    except subprocess.CalledProcessError as e:
        print(f"[ОШИБКА] Ошибка запуска docker: {e}")
        sys.exit(1)
