import os
import shutil
import subprocess
import sys
import parsers.python as pp
import parsers.java as jp
import parsers.go as gp

def copy_project(repo_or_path: str, build_path: str):
    """
    Копирует проект по ссылке GitHub или локальному пути во временную директорию.
    """
    # Создаем директорию для сборки, если она еще не создана
    os.makedirs(build_path, exist_ok=True)

    if repo_or_path.startswith("http"):
        print(f"Клонирование репозитория {repo_or_path}...")

        try:
            # Используем subprocess для выполнения команды git clone
            # Клонируем в указанный build_path
            # capture_output=True для скрытия стандартного вывода git
            subprocess.run(
                ["git", "clone", repo_or_path, build_path],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print("Клонирование успешно завершено.")
        except subprocess.CalledProcessError as e:
            print(f"ОШИБКА клонирования Git: {e.stderr.decode('utf-8')}")
            sys.exit(1)  # Завершаем программу в случае ошибки

    else:
        # Проверяем существование локальной папки
        if not os.path.isdir(repo_or_path):
            print(f"ОШИБКА: Локальная директория не найдена: {repo_or_path}")
            sys.exit(1)

        print(f"Копирование файлов из {repo_or_path} в {build_path}...")

        # shutil.copytree используется для рекурсивного копирования содержимого директории
        # dirs_exist_ok=True позволяет скопировать содержимое в уже существующий build_path
        # (хотя в вашем случае build_path создается внутри TemporaryDirectory и должен быть пустым)
        try:
            shutil.copytree(repo_or_path, build_path, dirs_exist_ok=True)
            print("Копирование успешно завершено.")
        except Exception as e:
            print(f"ОШИБКА копирования: {e}")
            sys.exit(1)

    # При успешном выполнении возвращаем путь к проекту
    return build_path

languages = {
    "python": [
        [".py"],
        ["requirements.txt", "pyproject.toml", "setup.py", "environment.yml"]
    ],
    "java": [
        [".java", ".kt", ".kts"],
        ["pom.xml", "build.gradle", "build.gradle.kts"]
    ],
    "js": [
        [".js", ".jsx", ".ts", ".tsx"],
        ["package.json", "webpack.config.js"]
    ],
    "go": [
        [".go"],
        ["go.mod", "go.sum"]
    ]
}


def pars_lang(path: str, external_lang: str = None) -> str:
    """
    Рекурсивно сканирует директорию проекта для определения основного языка.
    Использует систему скоринга на основе файлов манифестов и расширений.
    Полностью кроссплатформенная версия (учитывает нечувствительность к регистру Windows).
    """
    # Если язык явно указан, используем его
    if external_lang and external_lang.lower() in languages:
        lang = external_lang.lower()
        print(f"Используем язык '{lang}' указанный пользователем.")
        return lang

    print("Парсим язык программирования по структуре проекта...")

    # Система скоринга
    scores = {lang: 0 for lang in languages.keys()}

    # Преобразуем входящие манифесты и расширения к нижнему регистру для кроссплатформенного сравнения
    manifests_lower = {
        lang: [m.lower() for m in config[1]] for lang, config in languages.items()
    }
    extensions_lower = {
        lang: [e.lower() for e in config[0]] for lang, config in languages.items()
    }

    # --- Кроссплатформенное сканирование ---
    for root, _, files in os.walk(path):

        # 1. Готовим список файлов в текущей директории в нижнем регистре
        # (для нечувствительного к регистру поиска на Windows)
        files_lower = [f.lower() for f in files]

        for lang in languages.keys():

            # Манифест-файлы (наивысший приоритет)
            for manifest_name_lower in manifests_lower[lang]:
                if manifest_name_lower in files_lower:
                    # Присваиваем больше очков, чем за простой файл кода
                    scores[lang] += 10

            # Файлы кода
            for file in files:
                ext = os.path.splitext(file)[1].lower()

                # Используем список расширений в нижнем регистре
                if ext in extensions_lower[lang]:
                    scores[lang] += 1

    # Определение языка с максимальным счетом
    best_lang, max_score = "", 0
    if scores:
        best_lang, max_score = max(scores.items(), key=lambda item: item[1])

    # Проверка результата
    if max_score > 0:
        print(f"Определен язык: '{best_lang}' (Счет: {max_score})")
        return best_lang

    print("Автоматически определить язык не удалось.")
    sys.exit(1)


parsers = {
    "python": pp.parse_image_and_create_bash,
    "java": jp.parse_image_and_create_bash,
    "kotlin": jp.parse_image_and_create_bash,
    "go": gp.parse_image_and_create_bash,
}

def create_docker_image_and_bash(lang: str, path: str):
    print("Создаём файл сборки docker и bash скрипт установки зависимостей и запуска")

    # Создаём баш файл в котором мы установим зависимости и запустим проект
    # Обращаемся к парсеру конкретного ЯП для определения необходимой версии образа
    image = parsers.get(lang)(path)

    docker_image = f"""
    FROM {image}
    
    WORKDIR /app
    COPY . .
    
    RUN chmod +x /app/run.sh
    ENTRYPOINT ["/app/run.sh"]
    """

    print(f"Создание файла Dockerfile в {path}...")

    dockerfile_path = os.path.join(path, "Dockerfile")
    print(f"Создание файла Dockerfile в {dockerfile_path}...")

    try:
        with open(dockerfile_path, 'w', encoding='utf-8') as f:
            f.write(docker_image.strip() + "\n")
        print("Dockerfile успешно создан.")
    except IOError as e:
        print(f"ОШИБКА записи Dockerfile: {e}")
        sys.exit(1)