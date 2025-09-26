import argparse
import sys
import os
import tempfile
import parser as p
import dockers as d


def print_logo():
    print("""
      ╱$$$$$$              ╱$$                                         ╱$$                        
     ╱$$__  $$            │ $$                                        │ $$                  ╱$$   
    │ $$  ╲ $$ ╱$$   ╱$$ ╱$$$$$$    ╱$$$$$$  ╱$$$$$$╱$$$$   ╱$$$$$$  ╱$$$$$$    ╱$$$$$$    │ $$   
    │ $$$$$$$$│ $$  │ $$│_  $$_╱   ╱$$__  $$│ $$_  $$_  $$ │____  $$│_  $$_╱   │____  $$ ╱$$$$$$$$
    │ $$__  $$│ $$  │ $$  │ $$    │ $$  ╲ $$│ $$ ╲ $$ ╲ $$  ╱$$$$$$$  │ $$      ╱$$$$$$$│__  $$__╱
    │ $$  │ $$│ $$  │ $$  │ $$ ╱$$│ $$  │ $$│ $$ │ $$ │ $$ ╱$$__  $$  │ $$ ╱$$ ╱$$__  $$   │ $$   
    │ $$  │ $$│  $$$$$$╱  │  $$$$╱│  $$$$$$╱│ $$ │ $$ │ $$│  $$$$$$$  │  $$$$╱│  $$$$$$$   │__╱   
    │__╱  │__╱ ╲______╱    ╲___╱   ╲______╱ │__╱ │__╱ │__╱ ╲_______╱   ╲___╱   ╲_______╱          
""")


def main():
    parser = argparse.ArgumentParser(
        description="Automata+ это утилита для сборки и запуска проектов в Docker по GitHub ссылке или директории.",
        add_help=False
    )

    parser.add_argument(
        "repo_or_path",
        nargs='?',
        help="Ссылка на GitHub или путь к проекту"
    )

    parser.add_argument(
        "--languages",
        action='store_true',
        help="Показать список поддерживаемых языков программирования"
    )

    parser.add_argument(
        "-h", "--help",
        action="help",
        default=argparse.SUPPRESS,
        help="Показать это справочное сообщение и выйти"
    )

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(0)

    args = parser.parse_args()

    if args.languages:
        print("Поддерживаемые языки: python, java, kotlin, js, go")
        sys.exit(0)

    if not args.repo_or_path:
        parser.error("Ошибка: Ссылка на GitHub или путь к проекту (repo_or_path) обязательна для запуска.")

    print_logo()

    # Основная логика
    with tempfile.TemporaryDirectory() as tmpdir:
        build_path = os.path.join(tmpdir, "build")
        p.copy_project(args.repo_or_path, build_path)
        d.start_docker(p.pars_lang(build_path), build_path)


if __name__ == "__main__":
    main()
