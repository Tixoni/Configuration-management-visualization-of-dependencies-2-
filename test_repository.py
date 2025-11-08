"""
Модуль для работы с тестовым репозиторием
"""

import os
import json
from typing import Dict, Any, Optional


class TestRepository:
    """Класс для работы с локальным тестовым репозиторием"""
    
    def __init__(self, repo_path: str = "./test-repo"):
        # Нормализуем путь - преобразуем относительные пути в абсолютные
        # Сохраняем оригинальный путь для отладки
        original_path = repo_path
        current_dir = os.getcwd()
        
        # Сначала нормализуем путь (убирает ./ и ../)
        normalized = os.path.normpath(repo_path)
        
        if not os.path.isabs(normalized):
            # Получаем абсолютный путь относительно текущей рабочей директории
            self.repo_path = os.path.abspath(normalized)
        else:
            self.repo_path = normalized
        
        print(f"Инициализация локального репозитория:")
        print(f"  Оригинальный путь: '{original_path}'")
        print(f"  Нормализованный путь: '{normalized}'")
        print(f"  Абсолютный путь: '{self.repo_path}'")
        print(f"  Текущая рабочая директория: {current_dir}")
        print(f"  Путь существует: {os.path.exists(self.repo_path)}")
        if os.path.exists(self.repo_path):
            print(f"  Это директория: {os.path.isdir(self.repo_path)}")
        else:
            # Пробуем найти относительно текущей директории
            alt_path = os.path.join(current_dir, normalized)
            if os.path.exists(alt_path):
                print(f"  Найден альтернативный путь: {alt_path}")
                self.repo_path = alt_path
        
        self.packages = {}
        self._load_packages()
    
    def _load_packages(self):
        """Загружает пакеты из локального репозитория"""
        if not os.path.exists(self.repo_path):
            print(f"ОШИБКА: Тестовый репозиторий не найден: {self.repo_path}")
            print(f"Попытка найти альтернативные пути...")
            # Пробуем найти относительно текущей директории
            alt_path = os.path.join(os.getcwd(), self.repo_path if os.path.isabs(self.repo_path) else os.path.basename(self.repo_path))
            if os.path.exists(alt_path) and os.path.isdir(alt_path):
                print(f"Найден альтернативный путь: {alt_path}")
                self.repo_path = alt_path
            else:
                return
        
        if not os.path.isdir(self.repo_path):
            print(f"ОШИБКА: Указанный путь не является директорией: {self.repo_path}")
            return
        
        # Ищем JSON файлы с описанием пакетов
        json_files_found = 0
        try:
            files_in_dir = os.listdir(self.repo_path)
            print(f"Файлы в директории {self.repo_path}: {files_in_dir}")
        except Exception as e:
            print(f"ОШИБКА: Не удалось прочитать директорию {self.repo_path}: {e}")
            return
        
        for filename in files_in_dir:
            if filename.endswith('.json'):
                json_files_found += 1
                file_path = os.path.join(self.repo_path, filename)
                print(f"Обработка файла: {file_path}")
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        package_data = json.load(f)
                        package_name = package_data.get('name')
                        if package_name:
                            self.packages[package_name] = package_data
                            print(f"[OK] Загружен тестовый пакет: {package_name} из {filename}")
                        else:
                            print(f"[WARN] Предупреждение: файл {filename} не содержит поля 'name'")
                except json.JSONDecodeError as e:
                    print(f"[ERROR] Ошибка парсинга JSON в файле {filename}: {e}")
                except Exception as e:
                    print(f"[ERROR] Ошибка загрузки пакета из {filename}: {e}")
        
        if json_files_found == 0:
            print(f"[WARN] Предупреждение: в репозитории {self.repo_path} не найдено JSON файлов")
        elif len(self.packages) == 0:
            print(f"[WARN] Предупреждение: в репозитории {self.repo_path} не удалось загрузить ни одного пакета")
        else:
            print(f"[OK] Загружено пакетов из локального репозитория: {len(self.packages)} (пакеты: {', '.join(self.packages.keys())})")
    
    def get_package(self, package_name: str, version: str = "latest") -> Optional[Dict[str, Any]]:
        """Возвращает информацию о пакете из тестового репозитория"""
        if package_name in self.packages:
            package_data = self.packages[package_name]
            # Для простоты возвращаем последнюю версию
            return {
                "name": package_data["name"],
                "version": package_data.get("version", "1.0.0"),
                "dependencies": package_data.get("dependencies", {})
            }
        return None
    
    def package_exists(self, package_name: str) -> bool:
        """Проверяет существование пакета в тестовом репозитории"""
        return package_name in self.packages