#!/usr/bin/env python3
"""
Главный файл приложения - визуализатора графа зависимостей
"""

import os
import sys
from dependency_visualizer import DependencyVisualizer


def create_sample_config():
    """Создание примерного конфигурационного файла"""
    sample_config = """# Конфигурация анализатора зависимостей
package_name: express
repository_url: https://registry.npmjs.org
test_repository_mode: false
package_version: latest
output_filename: dependency_graph.txt
ascii_tree_output: true
max_depth: 2
filter_substring:
"""
    
    with open("config.yaml", "w", encoding="utf-8") as f:
        f.write(sample_config)
    print("Создан пример конфигурационного файла: config.yaml")


def main():
    """Точка входа в приложение"""
    # Создаем пример конфига если его нет
    if not os.path.exists("config.yaml"):
        print("Конфигурационный файл не найден.")
        create_sample_config()
        print("Запустите программу снова для использования созданного конфигурационного файла.")
        return
    
    # Проверяем аргументы командной строки
    config_file = "config.yaml"
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
        print(f"Используется конфигурационный файл: {config_file}")
    
    # Создаем и запускаем визуализатор
    visualizer = DependencyVisualizer(config_file)
    visualizer.run()


if __name__ == "__main__":
    main()