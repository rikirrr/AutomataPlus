import os
import sys
import re
import xml.etree.ElementTree as ET

java_environments = {
    "maven": {
        "manifest": "pom.xml",
        "install_cmd": "mvn clean install -DskipTests",
        "run_cmd": "mvn spring-boot:run",
        "build_cmd": "mvn clean package -DskipTests"
    },
    "gradle": {
        "manifest": "build.gradle",
        "install_cmd": "./gradlew build -x test",
        "run_cmd": "./gradlew bootRun",
        "build_cmd": "./gradlew build -x test"
    },
    "gradle_kts": {
        "manifest": "build.gradle.kts",
        "install_cmd": "./gradlew build -x test",
        "run_cmd": "./gradlew bootRun",
        "build_cmd": "./gradlew build -x test"
    }
}


def extract_java_version(path: str, environment: str) -> str:
    """
    Извлекает версию Java из файлов проекта.
    Возвращает версию в формате '17' или дефолтную '17'.
    """
    default_version = "17"

    if environment == "maven":
        pom_path = os.path.join(path, "pom.xml")
        if os.path.exists(pom_path):
            try:
                tree = ET.parse(pom_path)
                root = tree.getroot()

                # Убираем namespace для упрощения поиска
                for elem in root.iter():
                    if '}' in elem.tag:
                        elem.tag = elem.tag.split('}')[1]

                # Ищем версию Java в properties
                properties = root.find('.//properties')
                if properties is not None:
                    # Проверяем различные варианты указания версии Java
                    version_tags = [
                        'java.version',
                        'maven.compiler.source',
                        'maven.compiler.target',
                        'maven.compiler.release'
                    ]

                    for tag in version_tags:
                        version_elem = properties.find(tag)
                        if version_elem is not None and version_elem.text:
                            version = version_elem.text.strip()
                            # Извлекаем числовую версию (11, 17, 21 и т.д.)
                            version_match = re.search(r'(\d+)', version)
                            if version_match:
                                print(f"Maven: найдена Java версия {version_match.group(1)} в {tag}")
                                return version_match.group(1)

                # Ищем в maven-compiler-plugin
                plugins = root.findall('.//plugin')
                for plugin in plugins:
                    artifact_id = plugin.find('artifactId')
                    if artifact_id is not None and artifact_id.text == 'maven-compiler-plugin':
                        config = plugin.find('configuration')
                        if config is not None:
                            for version_tag in ['source', 'target', 'release']:
                                version_elem = config.find(version_tag)
                                if version_elem is not None and version_elem.text:
                                    version = version_elem.text.strip()
                                    version_match = re.search(r'(\d+)', version)
                                    if version_match:
                                        print(
                                            f"Maven: найдена Java версия {version_match.group(1)} в maven-compiler-plugin/{version_tag}")
                                        return version_match.group(1)

            except Exception as e:
                print(f"Предупреждение: не удалось парсить pom.xml: {e}")


    elif environment in ["gradle", "gradle_kts"]:

        build_file = "build.gradle" if environment == "gradle" else "build.gradle.kts"

        build_path = os.path.join(path, build_file)

        if os.path.exists(build_path):

            try:

                with open(build_path, "r", encoding="utf-8") as f:

                    content = f.read()

                print(f"Gradle: анализируем файл {build_file}")

                # --- Добавлена/Улучшена поддержка Kotlin DSL (jvmToolchain) ---

                jvm_toolchain_patterns = [

                    # 1. Kotlin DSL: kotlin { jvmToolchain(21) } (самый специфичный, с учетом переносов строк/пробелов)

                    r'kotlin\s*\{[^}]*?jvmToolchain\s*\(\s*(\d+)\s*\)',

                    # 2. Kotlin DSL/Groovy: jvmToolchain(21) / jvmToolchain = 21 (напрямую в build.gradle)

                    r'(?:^\s*|\s+)?jvmToolchain\s*(?:=|\()\s*(\d+)\s*(?:\)|\s|$)',

                    # 3. Kotlin DSL/Groovy: kotlin { jvmToolchain = 21 }

                    r'kotlin\s*\{[^}]*?jvmToolchain\s*=\s*(\d+)',

                    # 4. Kotlin DSL/Groovy: kotlin { jvmToolchain(JavaVersion.toVersion(21)) }

                    r'kotlin\s*\{[^}]*?jvmToolchain\s*\([^)]*?(\d+)[^)]*\)',

                ]

                for i, pattern in enumerate(jvm_toolchain_patterns):

                    # Используем re.DOTALL для обработки многострочных блоков, таких как kotlin { ... }

                    matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)

                    if matches:
                        version = matches[0].strip() if isinstance(matches[0], str) else matches[0][0].strip()

                        print(
                            f"Gradle: найдена Java версия {version} по паттерну {i + 1}: jvmToolchain (Kotlin/Groovy)")

                        return version

                # Java toolchain API паттерны

                # ... (остальные паттерны без изменений)

                toolchain_patterns = [

                    r'toolchain\s*\{[^}]*?languageVersion\s*=\s*JavaLanguageVersion\.of\s*\(\s*(\d+)\s*\)',

                    r'toolchain\.languageVersion\s*=\s*JavaLanguageVersion\.of\s*\(\s*(\d+)\s*\)',

                    r'java\s*\{[^}]*?toolchain\s*\{[^}]*?languageVersion\s*=\s*JavaLanguageVersion\.of\s*\(\s*(\d+)\s*\)',

                ]

                for i, pattern in enumerate(toolchain_patterns):

                    match = re.search(pattern, content, re.DOTALL)

                    if match:
                        print(f"Gradle: найдена Java версия {match.group(1)} по паттерну toolchain API {i + 1}")

                        return match.group(1)

                # Классические паттерны Gradle

                classic_patterns = [

                    (r'sourceCompatibility\s*=\s*["\']?(\d+)["\']?', 'sourceCompatibility'),

                    (r'targetCompatibility\s*=\s*["\']?(\d+)["\']?', 'targetCompatibility'),

                    (r'JavaVersion\.VERSION_(\d+)', 'JavaVersion.VERSION_'),

                    (r'javaVersion\s*=\s*["\']?(\d+)["\']?', 'javaVersion'),

                    (r'java\s*\{[^}]*sourceCompatibility\s*=\s*["\']?(\d+)["\']?', 'java{sourceCompatibility}'),

                    (r'java\s*\{[^}]*targetCompatibility\s*=\s*["\']?(\d+)["\']?', 'java{targetCompatibility}'),

                    (r'sourceCompatibility\s*=\s*JavaVersion\.VERSION_(\d+)', 'sourceCompatibility=JavaVersion'),

                    (r'targetCompatibility\s*=\s*JavaVersion\.VERSION_(\d+)', 'targetCompatibility=JavaVersion'),

                ]

                for pattern, name in classic_patterns:

                    match = re.search(pattern, content, re.DOTALL)

                    if match:
                        print(f"Gradle: найдена Java версия {match.group(1)} в {name}")

                        return match.group(1)


            except Exception as e:

                print(f"Предупреждение: не удалось прочитать {build_file}: {e}")


        # Проверяем gradle.properties
        gradle_props_path = os.path.join(path, "gradle.properties")
        if os.path.exists(gradle_props_path):
            try:
                with open(gradle_props_path, "r", encoding="utf-8") as f:
                    content = f.read()

                patterns = [
                    (r'java\.version\s*=\s*(\d+)', 'java.version'),
                    (r'javaVersion\s*=\s*(\d+)', 'javaVersion'),
                    (r'sourceCompatibility\s*=\s*(\d+)', 'sourceCompatibility'),
                    (r'targetCompatibility\s*=\s*(\d+)', 'targetCompatibility'),
                    (r'kotlin\.jvm\.target\s*=\s*(\d+)', 'kotlin.jvm.target'),
                    (r'org\.gradle\.java\.home\s*=.*jdk-?(\d+)', 'org.gradle.java.home')
                ]

                for pattern, name in patterns:
                    match = re.search(pattern, content)
                    if match:
                        print(f"gradle.properties: найдена Java версия {match.group(1)} в {name}")
                        return match.group(1)

            except Exception as e:
                print(f"Предупреждение: не удалось прочитать gradle.properties: {e}")

        # Проверяем libs.versions.toml (Version Catalog)
        libs_versions_path = os.path.join(path, "gradle", "libs.versions.toml")
        if os.path.exists(libs_versions_path):
            try:
                with open(libs_versions_path, "r", encoding="utf-8") as f:
                    content = f.read()

                patterns = [
                    (r'java\s*=\s*["\'](\d+)["\']', 'java'),
                    (r'jvm\s*=\s*["\'](\d+)["\']', 'jvm'),
                    (r'kotlin-jvm\s*=\s*["\'](\d+)["\']', 'kotlin-jvm')
                ]

                for pattern, name in patterns:
                    match = re.search(pattern, content)
                    if match:
                        print(f"libs.versions.toml: найдена Java версия {match.group(1)} в {name}")
                        return match.group(1)

            except Exception as e:
                print(f"Предупреждение: не удалось прочитать libs.versions.toml: {e}")

    # Проверяем .java-version файл (аналог .python-version)
    java_version_path = os.path.join(path, ".java-version")
    if os.path.exists(java_version_path):
        try:
            with open(java_version_path, "r", encoding="utf-8") as f:
                version = f.read().strip()
                version_match = re.search(r'(\d+)', version)
                if version_match:
                    print(f".java-version: найдена Java версия {version_match.group(1)}")
                    return version_match.group(1)
        except Exception as e:
            print(f"Предупреждение: не удалось прочитать .java-version: {e}")

    print(f"Версия Java не найдена, используется дефолтная: {default_version}")
    return default_version


def get_docker_image(java_version: str) -> str:
    """
    Возвращает подходящий Docker образ для версии Java.
    """
    return f"openjdk:{java_version}-jdk-slim"


def detect_spring_boot(path: str, environment: str) -> bool:
    """
    Определяет, является ли проект Spring Boot приложением.
    """
    if environment == "maven":
        pom_path = os.path.join(path, "pom.xml")
        if os.path.exists(pom_path):
            try:
                with open(pom_path, "r", encoding="utf-8") as f:
                    content = f.read()
                return "spring-boot" in content.lower()
            except Exception:
                pass

    elif environment in ["gradle", "gradle_kts"]:
        build_file = "build.gradle" if environment == "gradle" else "build.gradle.kts"
        build_path = os.path.join(path, build_file)
        if os.path.exists(build_path):
            try:
                with open(build_path, "r", encoding="utf-8") as f:
                    content = f.read()
                return "spring-boot" in content.lower()
            except Exception:
                pass

    return False


def find_main_class(path: str) -> str:
    """
    Пытается найти главный класс с методом main.
    """
    # Ищем в src/main/java
    java_dir = os.path.join(path, "src", "main", "java")
    if os.path.exists(java_dir):
        for root, dirs, files in os.walk(java_dir):
            for file in files:
                if file.endswith(".java"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            # Ищем public static void main
                            if re.search(r'public\s+static\s+void\s+main\s*\(', content):
                                # Извлекаем package и class name
                                package_match = re.search(r'package\s+([^;]+);', content)
                                class_match = re.search(r'public\s+class\s+(\w+)', content)

                                if package_match and class_match:
                                    package = package_match.group(1).strip()
                                    class_name = class_match.group(1).strip()
                                    return f"{package}.{class_name}"
                                elif class_match:
                                    return class_match.group(1).strip()
                    except Exception:
                        continue

    return "Application"  # Дефолтное имя


def parse_image_and_create_bash(path: str) -> str:
    """
    Парсит структуру проекта Java для определения среды (Maven/Gradle)
    и генерирует скрипт запуска run.sh. Возвращает имя базового образа.
    """
    print("Парсим докер образ из структуры проекта (Java)...")

    environment = None
    env_config = None

    # Определяем среду сборки
    for key, config in java_environments.items():
        if os.path.exists(os.path.join(path, config["manifest"])):
            environment = key
            env_config = config
            break

    if environment is None:
        print("ОШИБКА: Не найден Maven или Gradle проект")
        sys.exit(1)

    # Определяем версию Java
    java_version = extract_java_version(path, environment)
    docker_image = get_docker_image(java_version)

    # Определяем тип приложения
    is_spring_boot = detect_spring_boot(path, environment)
    main_class = find_main_class(path) if not is_spring_boot else None

    print(f"Обнаружена среда: {environment}")
    print(f"Версия Java: {java_version}")
    print(f"Docker образ: {docker_image}")
    print(f"Spring Boot: {'Да' if is_spring_boot else 'Нет'}")
    if main_class:
        print(f"Главный класс: {main_class}")

    # Генерируем содержимое run.sh в зависимости от среды
    if environment == "maven":
        run_sh_content = f"""#!/bin/bash
set -e

# Установка Maven
echo "Устанавливаем Maven..."
apt-get update
apt-get install -y maven
rm -rf /var/lib/apt/lists/*

# Скачиваем зависимости для кэширования
echo "Скачиваем зависимости Maven..."
mvn dependency:go-offline -B

# Установка зависимостей и сборка
echo "Собираем проект..."
{env_config["build_cmd"]}

# Запуск приложения
if [ "{is_spring_boot}" = "True" ]; then
    echo "Запускаем Spring Boot приложение..."
    exec {env_config["run_cmd"]}
else
    echo "Ищем JAR файл..."
    JAR_FILE=$(find target -name "*.jar" | head -1)

    if [ -z "$JAR_FILE" ]; then
        echo "ОШИБКА: JAR файл не найден в target/"
        exit 1
    fi

    echo "Запускаем приложение: $JAR_FILE"
    exec java -jar "$JAR_FILE"
fi
"""

    elif environment in ["gradle", "gradle_kts"]:
        # Проверяем наличие gradlew
        gradlew_path = os.path.join(path, "gradlew")
        gradle_cmd = "./gradlew" if os.path.exists(gradlew_path) else "gradle"

        run_sh_content = f"""#!/bin/bash
set -e

# Установка Gradle если нет wrapper'а
if [ ! -f "./gradlew" ]; then
    echo "Устанавливаем Gradle..."
    apt-get update
    apt-get install -y gradle
    rm -rf /var/lib/apt/lists/*
fi

# Делаем gradlew исполняемым если он существует
if [ -f "./gradlew" ]; then
    chmod +x ./gradlew
    echo "Скачиваем зависимости Gradle..."
    ./gradlew dependencies --no-daemon || true
else
    echo "Скачиваем зависимости Gradle..."
    gradle dependencies || true
fi

# Установка зависимостей и сборка
echo "Собираем проект..."
{gradle_cmd} build -x test

# Запуск приложения
if [ "{is_spring_boot}" = "True" ]; then
    echo "Запускаем Spring Boot приложение..."
    exec {gradle_cmd} bootRun
else
    echo "Ищем JAR файл..."
    JAR_FILE=$(find build/libs -name "*.jar" | grep -v sources | grep -v javadoc | head -1)

    if [ -z "$JAR_FILE" ]; then
        echo "ОШИБКА: JAR файл не найден в build/libs/"
        exit 1
    fi

    echo "Запускаем приложение: $JAR_FILE"
    exec java -jar "$JAR_FILE"
fi
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