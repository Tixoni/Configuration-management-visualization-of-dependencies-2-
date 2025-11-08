#!/usr/bin/env python3
"""
Главный файл приложения - визуализатора графа зависимостей
"""

import os
import sys
from dependency_visualizer import DependencyVisualizer



def main():
    """Точка входа в приложение"""
    # Создаем пример конфига если его нет
    if not os.path.exists("config.yaml"):
        print("Конфигурационный файл не найден.")
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