import subprocess
import sys
import uuid
import parser as p


def start_docker(lang: str, path: str):
    p.create_docker_image_and_bash(lang, path)

    container_name = f"{lang}_{uuid.uuid4().hex[:8]}"
    print(f"Контейнер: {container_name}")

    try:
        print("Сборка образа...")
        build_result = subprocess.run(
            ["docker", "build", "-t", container_name, path],
            capture_output=True,
            text=True,
            encoding='utf-8',
            check=True
        )
        print("Образ собран")
        print("Запуск контейнера.")
        run_result = subprocess.run(
            ["docker", "run", "--rm", container_name],
            capture_output=True,
            text=True,
            encoding='utf-8',
            check=True
        )
        print("Контейнер выполнен успешно!")
        print("Вывод:")
        print(run_result.stdout)
        print(build_result.stdout)


    except subprocess.CalledProcessError as e:
        print(f"ОШИБКА: {e.stderr}")
        print(f"STDOUT: {e.stdout}")
        sys.exit(1)