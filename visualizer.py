#!/usr/bin/env python3
"""
Визуализатор графа зависимостей с реальным получением зависимостей
БЕЗ ИСПОЛЬЗОВАНИЯ ГОТОВЫХ МЕНЕДЖЕРОВ ПАКЕТОВ
"""

import sys
import os
import re
import json
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Set, Tuple
import datetime


class ConfigError(Exception):
    """Исключение для ошибок конфигурации"""
    pass


class NetworkError(Exception):
    """Исключение для ошибок сети"""
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
                
                # Удаляем комментарии из значения (всё что после #)
                if '#' in value:
                    value = value.split('#')[0].strip()
                
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


class RepositoryClient:
    """Клиент для получения зависимостей из репозиториев"""
    
    @staticmethod
    def detect_repository_type(repo_url: str) -> str:
        """Определяет тип репозитория по URL"""
        if 'npmjs.org' in repo_url or 'registry.npmjs.org' in repo_url:
            return 'npm'
        elif 'pypi.org' in repo_url or 'pypi.python.org' in repo_url:
            return 'pypi'
        elif 'repo1.maven.org' in repo_url or 'maven.org' in repo_url:
            return 'maven'
        elif 'github.com' in repo_url:
            return 'npm'
        else:
            return 'generic'
    
    @staticmethod
    def fetch_npm_package_info(package_name: str, version: str = "latest") -> Dict[str, Any]:
        """Получает информацию о NPM пакете"""
        try:
            url = f"https://registry.npmjs.org/{package_name}"
            if version != "latest":
                url = f"https://registry.npmjs.org/{package_name}/{version}"
            
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode())
                return data
        except urllib.error.URLError as e:
            raise NetworkError(f"Ошибка получения NPM пакета {package_name}: {e}")
        except Exception as e:
            raise NetworkError(f"Ошибка обработки NPM пакета {package_name}: {e}")
    
    @staticmethod
    def fetch_pypi_package_info(package_name: str, version: str = "latest") -> Dict[str, Any]:
        """Получает информацию о Python пакете"""
        try:
            url = f"https://pypi.org/pypi/{package_name}/json"
            
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode())
                
                # Определяем версию
                if version == "latest":
                    version = data['info']['version']
                
                # Получаем зависимости для конкретной версии
                if version in data['releases']:
                    release_info = data['releases'][version]
                    # Для PyPI зависимости находятся в info
                    return {
                        'info': data['info'],
                        'version': version,
                        'dependencies': data['info'].get('requires_dist', [])
                    }
                else:
                    raise NetworkError(f"Версия {version} не найдена для пакета {package_name}")
                    
        except urllib.error.URLError as e:
            raise NetworkError(f"Ошибка получения PyPI пакета {package_name}: {e}")
        except Exception as e:
            raise NetworkError(f"Ошибка обработки PyPI пакета {package_name}: {e}")
    
    @staticmethod
    def extract_dependencies(package_info: Dict[str, Any], repo_type: str) -> Dict[str, str]:
        """Извлекает зависимости из информации о пакете"""
        dependencies = {}
        
        if repo_type == 'npm':
            # Для NPM получаем последнюю версию и её зависимости
            if 'dist-tags' in package_info and 'versions' in package_info:
                latest_version = package_info['dist-tags']['latest']
                version_data = package_info['versions'].get(latest_version, {})
                
                # Получаем зависимости с реальными версиями
                deps = version_data.get('dependencies', {})
                for dep, version in deps.items():
                    dependencies[dep] = version  # ← СОХРАНЯЕМ РЕАЛЬНУЮ ВЕРСИЮ
        
        elif repo_type == 'pypi':
            # Для PyPI зависимости находятся в 'info']['requires_dist'
            deps = package_info.get('info', {}).get('requires_dist', [])
            if deps:
                for dep in deps:
                    # Парсим строку типа "package>=1.0.0"
                    dep_name = re.split(r'[<>=!\[\];]', dep)[0].strip()
                    if dep_name and not dep_name.startswith('python_'):
                        # Для PyPI сложно получить точные версии, оставляем как есть
                        dependencies[dep_name] = dep.strip()
        
        return dependencies


class DependencyAnalyzer:
    """Анализатор зависимостей"""
    
    def __init__(self, max_depth: int = 3, filter_str: str = ""):
        self.max_depth = max_depth
        self.filter_str = filter_str
        self.visited_packages: Set[Tuple[str, str]] = set()
        self.dependency_tree: Dict[str, Any] = {}
    
    def analyze_package(self, package_name: str, version: str = "latest", 
                   repo_url: str = "https://registry.npmjs.org", depth: int = 0) -> Dict[str, Any]:
    
        if depth >= self.max_depth:
            return {"name": package_name, "version": version, "dependencies": {}}
        
        cache_key = (package_name, version)
        if cache_key in self.visited_packages:
            return {"name": package_name, "version": version, "dependencies": {}, "cached": True}
        
        self.visited_packages.add(cache_key)
        
        try:
            print(f"Анализ {package_name}@{version} (уровень {depth})...")
            
            # Определяем тип репозитория
            repo_type = RepositoryClient.detect_repository_type(repo_url)
            
            # Получаем информацию о пакете
            if repo_type == 'npm':
                # Для NPM передаем только имя пакета, версию используем для получения правильных зависимостей
                package_info = RepositoryClient.fetch_npm_package_info(package_name, "latest")
            elif repo_type == 'pypi':
                package_info = RepositoryClient.fetch_pypi_package_info(package_name, version)
            else:
                raise NetworkError(f"Неподдерживаемый репозиторий: {repo_url}")
            
            # Извлекаем зависимости
            dependencies = RepositoryClient.extract_dependencies(package_info, repo_type)
            
            # Фильтруем зависимости если нужно
            if self.filter_str:
                dependencies = {k: v for k, v in dependencies.items() if self.filter_str in k}
            
            # Рекурсивно анализируем зависимости
            child_deps = {}
            for dep_name, dep_version in dependencies.items():
                try:
                    # Для рекурсивного анализа передаем имя пакета и реальную версию
                    child_deps[dep_name] = self.analyze_package(
                        dep_name, dep_version, repo_url, depth + 1  # ← ПЕРЕДАЕМ РЕАЛЬНУЮ ВЕРСИЮ
                    )
                except (NetworkError, Exception) as e:
                    child_deps[dep_name] = {
                        "name": dep_name, 
                        "version": dep_version,  # ← СОХРАНЯЕМ РЕАЛЬНУЮ ВЕРСИЮ ДАЖЕ ПРИ ОШИБКЕ
                        "error": str(e),
                        "dependencies": {}
                    }
            
            return {
                "name": package_name,
                "version": version,  # ← СОХРАНЯЕМ РЕАЛЬНУЮ ВЕРСИЮ
                "dependencies": child_deps
            }
            
        except Exception as e:
            return {
                "name": package_name,
                "version": version,  # ← СОХРАНЯЕМ РЕАЛЬНУЮ ВЕРСИЮ
                "error": str(e),
                "dependencies": {}
            }


class OutputCapture:
    """Класс для захвата вывода в консоль и записи в файл"""
    
    def __init__(self, log_filename: str = "output_log.txt"):
        self.log_filename = log_filename
        self.original_stdout = sys.stdout
        self.log_file = None
    
    def start_capture(self):
        """Начать захват вывода"""
        self.log_file = open(self.log_filename, 'w', encoding='utf-8')
        
        class DualOutput:
            def __init__(self, original, log_file):
                self.original = original
                self.log_file = log_file
            
            def write(self, text):
                self.original.write(text)
                self.log_file.write(text)
                self.log_file.flush()
            
            def flush(self):
                self.original.flush()
                self.log_file.flush()
        
        sys.stdout = DualOutput(self.original_stdout, self.log_file)
        
        # Записываем заголовок в лог
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'='*60}")
        print(f"ЛОГ ВЫПОЛНЕНИЯ - {timestamp}")
        print(f"{'='*60}")
    
    def stop_capture(self):
        """Остановить захват вывода"""
        if self.log_file:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n{'='*60}")
            print(f"ВЫПОЛНЕНИЕ ЗАВЕРШЕНО - {timestamp}")
            print(f"{'='*60}")
            
            sys.stdout = self.original_stdout
            self.log_file.close()
            print(f"\nПолный лог выполнения сохранен в: {self.log_filename}")


class DependencyVisualizer:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.output_capture = None
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
                        # Удаляем все нецифровые символы кроме минуса
                        clean_value = re.sub(r'[^\d-]', '', self.config[param])
                        if clean_value:
                            self.config[param] = int(clean_value)
                        else:
                            raise ValueError(f"Не могу преобразовать в число: {self.config[param]}")
                
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
    
    def display_config(self) -> None:
        """Вывод всех параметров конфигурации"""
        print("=" * 50)
        print("КОНФИГУРАЦИЯ ВИЗУАЛИЗАТОРА ЗАВИСИМОСТЕЙ")
        print("=" * 50)
        
        for key, value in self.config.items():
            print(f"{key:25}: {value} ({type(value).__name__})")
        
        print("=" * 50)
    
    def analyze_real_dependencies(self) -> Dict[str, Any]:
        """Реальный анализ зависимостей"""
        print(f"\nНачинаем анализ пакета: {self.config['package_name']}")
        print(f"Репозиторий: {self.config['repository_url']}")
        print(f"Версия: {self.config['package_version']}")
        print(f"Макс. глубина: {self.config['max_depth']}")
        
        if self.config['filter_substring']:
            print(f"Фильтр: '{self.config['filter_substring']}'")
        
        analyzer = DependencyAnalyzer(
            max_depth=self.config['max_depth'],
            filter_str=self.config['filter_substring']
        )
        
        dependency_tree = analyzer.analyze_package(
            package_name=self.config['package_name'],
            version="latest",  # ← ИСПРАВЛЕНО: всегда используем "latest" для корневого пакета
            repo_url=self.config['repository_url']
        )
        
        return dependency_tree
    
    def display_ascii_tree(self, tree: Dict[str, Any], prefix: str = "", is_last: bool = True):
        """Отображает ASCII-дерево зависимостей в консоль"""
        name = tree['name']
        version = tree.get('version', 'unknown')
        error = tree.get('error')
        
        # Текущий узел
        connector = "└── " if is_last else "├── "
        current_line = f"{prefix}{connector}{name}@{version}"
        
        if error:
            current_line += f" [ОШИБКА: {error}]"
        
        print(current_line)
        
        # Зависимости
        dependencies = tree.get('dependencies', {})
        if dependencies:
            new_prefix = prefix + ("    " if is_last else "│   ")
            dep_count = len(dependencies)
            
            for i, (dep_name, dep_tree) in enumerate(dependencies.items()):
                is_last_dep = (i == dep_count - 1)
                self.display_ascii_tree(dep_tree, new_prefix, is_last_dep)
    
    def save_tree_to_file(self, tree: Dict[str, Any]):
        try:
            # Генерируем имя файла на основе имени пакета
            package_name = tree['name']
            output_file = f"{package_name}_dependency_graph.txt"
            
            # Обновляем конфиг с новым именем файла
            self.config['output_filename'] = output_file
            
            with open(output_file, 'w', encoding='utf-8') as f:
                # Заголовок файла
                f.write(f"ГРАФ ЗАВИСИМОСТЕЙ\n")
                f.write(f"{'='*50}\n")
                f.write(f"Пакет: {tree['name']}@{tree.get('version', 'unknown')}\n")
                f.write(f"Репозиторий: {self.config['repository_url']}\n")
                f.write(f"Время генерации: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Максимальная глубина: {self.config['max_depth']}\n")
                
                if self.config['filter_substring']:
                    f.write(f"Фильтр: '{self.config['filter_substring']}'\n")
                
                f.write(f"{'='*50}\n\n")
                
                # Функция для рекурсивной записи дерева в файл
                def write_tree_to_file(tree_node, prefix="", is_last=True):
                    name = tree_node['name']
                    version = tree_node.get('version', 'unknown')
                    error = tree_node.get('error')
                    
                    connector = "└── " if is_last else "├── "
                    line = f"{prefix}{connector}{name}@{version}"
                    
                    if error:
                        line += f" [ОШИБКА: {error}]"
                    
                    f.write(line + "\n")
                    
                    # Рекурсивно записываем зависимости
                    dependencies = tree_node.get('dependencies', {})
                    if dependencies:
                        new_prefix = prefix + ("    " if is_last else "│   ")
                        dep_count = len(dependencies)
                        
                        for i, (dep_name, dep_tree) in enumerate(dependencies.items()):
                            is_last_dep = (i == dep_count - 1)
                            write_tree_to_file(dep_tree, new_prefix, is_last_dep)
                
                # Записываем основное дерево
                write_tree_to_file(tree)
                
                # Статистика
                f.write(f"\n{'='*50}\n")
                f.write("СТАТИСТИКА:\n")
                
                def count_dependencies(tree_node):
                    total = 1  # текущий пакет
                    for dep in tree_node.get('dependencies', {}).values():
                        total += count_dependencies(dep)
                    return total
                
                total_packages = count_dependencies(tree)
                f.write(f"Всего пакетов в графе: {total_packages}\n")
                f.write(f"Уровней вложенности: {self.config['max_depth']}\n")
            
            print(f"\nГраф зависимостей сохранен в файл: {output_file}")
            
        except Exception as e:
            print(f"Ошибка при сохранении файла {output_file}: {e}")
    
    def run(self) -> None:
        """Основной метод запуска приложения"""
        try:
            # Создаем лог-файл с именем на основе текущего времени
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"visualizer_log_{timestamp}.txt"
            
            # Начинаем захват вывода
            self.output_capture = OutputCapture(log_filename)
            self.output_capture.start_capture()
            
            # Основная логика
            self.display_config()
            
            # Реальный анализ зависимостей
            dependency_tree = self.analyze_real_dependencies()
            
            # Вывод результатов в консоль
            if self.config['ascii_tree_output']:
                print(f"\nДерево зависимостей для {self.config['package_name']}:")
                self.display_ascii_tree(dependency_tree)
            
            # Сохранение графа в текстовый файл
            self.save_tree_to_file(dependency_tree)
            
            print(f"\nАнализ завершен успешно!")
            
        except ConfigError as e:
            print(f"Ошибка конфигурации: {e}", file=sys.stderr)
            sys.exit(1)
        except NetworkError as e:
            print(f"Ошибка сети: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Неожиданная ошибка: {e}", file=sys.stderr)
            sys.exit(1)
        finally:
            # Всегда останавливаем захват вывода
            if self.output_capture:
                self.output_capture.stop_capture()


def create_sample_config():
    """Создание примерного конфигурационного файла"""
    sample_config = """# Конфигурация анализатора зависимостей
package_name: express
repository_url: https://registry.npmjs.org
test_repository_mode: false
package_version: latest
output_filename: dependency_graph.txt
ascii_tree_output: true
max_depth: 3
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