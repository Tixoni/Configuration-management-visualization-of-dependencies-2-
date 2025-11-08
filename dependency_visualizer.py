import os
import re
import datetime
import sys
from typing import Dict, Any
from yaml_parser import YAMLParser
from config_error import ConfigError
from network_error import NetworkError
from dependency_analyzer import DependencyAnalyzer
from output_capture import OutputCapture


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
        # Проверка максимальной глубина
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
            version="latest",
            repo_url=self.config['repository_url'],
            test_mode=self.config['test_repository_mode']
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
            # Используем имя файла из конфига, если указано, иначе генерируем
            if self.config['output_filename'] and self.config['output_filename'] != 'dependency_graph.txt':
                output_file = self.config['output_filename']
            else:
                package_name = tree['name']
                output_file = f"{package_name}_dependency_graph.txt"
            
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