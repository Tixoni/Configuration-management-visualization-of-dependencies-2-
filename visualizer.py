#!/usr/bin/env python3
"""
Минимальный прототип визуализатора графа зависимостей
Этап 1: Конфигурация и обработка параметров
БЕЗ ИСПОЛЬЗОВАНИЯ ГОТОВЫХ БИБЛИОТЕК
"""

import sys
import os
import re
from typing import Dict, Any, List, Optional


class ConfigError(Exception):
    """Исключение для ошибок конфигурации"""
    pass


class YAMLParser:
    """Простой парсер YAML-подобного формата без внешних библиотек"""
    
    @staticmethod
    def parse_yaml_file(file_path: str) -> Dict[str, Any]:
        """Парсинг простого YAML-файла без использования библиотек"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            return YAMLParser._parse_yaml_content(content)
            
        except Exception as e:
            raise ConfigError(f"Ошибка чтения файла конфигурации: {e}")
    
    @staticmethod
    def _parse_yaml_content(content: str) -> Dict[str, Any]:
        """Парсинг содержимого YAML"""
        config = {}
        lines = content.split('\n')
        line_number = 0
        
        for line in lines:
            line_number += 1
            line = line.strip()
            
            # Пропускаем пустые строки и комментарии
            if not line or line.startswith('#'):
                continue
            
            # Ищем ключ-значение разделенные двоеточием
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                # Обработка значений
                parsed_value = YAMLParser._parse_value(value)
                config[key] = parsed_value
        
        return config
    
    @staticmethod
    def _parse_value(value: str) -> Any:
        """Парсинг значения с определением типа"""
        if not value:
            return ""
        
        # Булевы значения
        if value.lower() in ['true', 'yes', 'on']:
            return True
        if value.lower() in ['false', 'no', 'off']:
            return False
        
        # Числовые значения
        if value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
            return int(value)
        
        # Числа с плавающей точкой
        if re.match(r'^-?\d+\.\d+$', value):
            return float(value)
        
        # Строки в кавычках
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            return value[1:-1]
        
        # Простые строки
        return value


class DependencyVisualizer:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.load_config()
    
    def load_config(self) -> None:
        """Загрузка конфигурации из YAML файла БЕЗ ВНЕШНИХ БИБЛИОТЕК"""
        try:
            if not os.path.exists(self.config_path):
                raise ConfigError(f"Конфигурационный файл не найден: {self.config_path}")
            
            self.config = YAMLParser.parse_yaml_file(self.config_path)
            
            if not self.config:
                raise ConfigError("Конфигурационный файл пуст или имеет неверный формат")
            
            self._validate_config()
            
        except Exception as e:
            raise ConfigError(f"Ошибка загрузки конфигурации: {e}")
    
    def _validate_config(self) -> None:
        """Валидация параметров конфигурации"""
        required_params = [
            'package_name',
            'repository_url', 
            'test_repository_mode',
            'package_version',
            'output_filename',
            'ascii_tree_output',
            'max_depth',
            'filter_substring'
        ]
        
        # Проверка наличия обязательных параметров
        for param in required_params:
            if param not in self.config:
                raise ConfigError(f"Отсутствует обязательный параметр: {param}")
        
        # Валидация типов и значений
        self._validate_parameter_types()
        self._validate_parameter_values()
    
    def _validate_parameter_types(self) -> None:
        """Проверка типов параметров"""
        # Приводим типы к ожидаемым
        type_conversions = {
            'package_name': str,
            'repository_url': str,
            'package_version': str,
            'output_filename': str,
            'filter_substring': str,
            'max_depth': int,
            'test_repository_mode': bool,
            'ascii_tree_output': bool
        }
        
        for param, expected_type in type_conversions.items():
            try:
                if expected_type == bool:
                    # Для булевых значений преобразуем строки
                    if isinstance(self.config[param], str):
                        if self.config[param].lower() in ['true', 'yes', 'on', '1']:
                            self.config[param] = True
                        elif self.config[param].lower() in ['false', 'no', 'off', '0']:
                            self.config[param] = False
                        else:
                            raise ValueError(f"Некорректное булево значение: {self.config[param]}")
                
                elif expected_type == int:
                    # Для целых чисел преобразуем строки
                    if isinstance(self.config[param], str):
                        self.config[param] = int(self.config[param])
                
                # Проверяем итоговый тип
                if not isinstance(self.config[param], expected_type):
                    raise ValueError(f"Ожидался тип {expected_type.__name__}")
                    
            except (ValueError, TypeError) as e:
                raise ConfigError(
                    f"Параметр '{param}' имеет неверный тип или значение: {e}"
                )
    
    def _validate_parameter_values(self) -> None:
        """Проверка значений параметров"""
        # Проверка максимальной глубины
        if self.config['max_depth'] < 1:
            raise ConfigError("Максимальная глубина анализа должна быть положительным числом")
        
        # Проверка имени файла вывода
        output_file = self.config['output_filename']
        if not output_file:
            raise ConfigError("Имя файла вывода не может быть пустым")
        
        # Проверка URL репозитория
        repo_url = self.config['repository_url']
        if not repo_url:
            raise ConfigError("URL репозитория не может быть пустым")
        
        # В тестовом режиме проверяем существование локального пути
        if self.config['test_repository_mode'] and not repo_url.startswith(('http://', 'https://')):
            if not os.path.exists(repo_url):
                raise ConfigError(f"Локальный репозиторий не найден: {repo_url}")
    
    def display_config(self) -> None:
        """Вывод всех параметров конфигурации"""
        print("=" * 50)
        print("КОНФИГУРАЦИЯ ВИЗУАЛИЗАТОРА ЗАВИСИМОСТЕЙ")
        print("=" * 50)
        
        for key, value in self.config.items():
            print(f"{key:25}: {value} ({type(value).__name__})")
        
        print("=" * 50)
    
    def simulate_dependency_analysis(self) -> None:
        """Симуляция анализа зависимостей (для демонстрации)"""
        print("\nСимуляция анализа зависимостей...")
        
        package_name = self.config['package_name']
        max_depth = self.config['max_depth']
        filter_str = self.config['filter_substring']
        
        # Симуляция дерева зависимостей
        if self.config['ascii_tree_output']:
            self._display_ascii_tree(package_name, max_depth)
        
        print(f"\nГраф зависимостей будет сохранен в: {self.config['output_filename']}")
        print("Анализ завершен успешно!")
    
    def _display_ascii_tree(self, package: str, depth: int) -> None:
        """Отображение ASCII-дерева зависимостей (демонстрация)"""
        print(f"\nДерево зависимостей для {package} (глубина: {depth}):")
        print(f"{package}")
        print("├── dependency-a")
        print("│   ├── sub-dep-1")
        if depth > 1:
            print("│   │   └── deep-dep-1")
        print("│   └── sub-dep-2")
        print("├── dependency-b")
        print("│   └── sub-dep-3")
        print("└── dependency-c")
        
        if self.config['filter_substring']:
            print(f"\nПрименен фильтр: '{self.config['filter_substring']}'")
    
    def run(self) -> None:
        """Основной метод запуска приложения"""
        try:
            self.display_config()
            self.simulate_dependency_analysis()
            
        except ConfigError as e:
            print(f"Ошибка конфигурации: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Неожиданная ошибка: {e}", file=sys.stderr)
            sys.exit(1)


def create_sample_config():
    """Создание примерного конфигурационного файла"""
    sample_config = """# Конфигурация анализатора зависимостей
package_name: example-package
repository_url: https://github.com/example/repo
test_repository_mode: false
package_version: 1.0.0
output_filename: dependency_graph.png
ascii_tree_output: true
max_depth: 3
filter_substring: test
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