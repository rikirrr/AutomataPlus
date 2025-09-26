import parser as p

def start_docker(lang: str, path: str):
    # Создаём Dockerfile
    image = p.create_docker_image_and_bash(lang, path)

    # Запускаем докер с случайным названием и выводим в консоль
