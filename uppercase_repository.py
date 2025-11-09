"""
Модуль для работы с тестовым репозиторием с пакетами в UPPERCASE
"""

import os
import json
import re
from typing import Dict, Any, Optional
from config_error import ConfigError


class UppercaseRepository:
    """Класс для работы с тестовым репозиторием где пакеты в UPPERCASE"""
    
    def __init__(self, repo_path: str):
        self.repo_path = os.path.normpath(repo_path)
        self.packages = {}
        self._load_repository_graph()
    
    def _load_repository_graph(self):
        """Загружает граф репозитория из файла"""
        if not os.path.exists(self.repo_path):
            raise ConfigError(f"Файл репозитория не найден: {self.repo_path}")
        
        try:
            with open(self.repo_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Парсим специальный формат графа
            self._parse_repository_graph(content)
            
        except Exception as e:
            raise ConfigError(f"Ошибка загрузки репозитория: {e}")
    
    def _parse_repository_graph(self, content: str):

        current_package = None
        lines = content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            i += 1
            
            # Пропускаем пустые строки и комментарии
            if not line or line.startswith('#'):
                continue
            
            # Проверяем что это имя пакета (UPPERCASE и нет отступа)
            if (re.match(r'^[A-Z][A-Z0-9_]*$', line) and 
                not lines[i-1].startswith((' ', '\t'))):
                
                package_name = line
                self._validate_uppercase_name(package_name, i)
                
                if package_name in self.packages:
                    raise ConfigError(f"Дублирующийся пакет {package_name} в строке {i}")
                
                self.packages[package_name] = {
                    'name': package_name,
                    'version': '1.0.0',
                    'dependencies': []
                }
                current_package = package_name
                
                # Читаем зависимости (строки с отступами)
                while i < len(lines) and lines[i].startswith((' ', '\t')):
                    dep_line = lines[i].strip()
                    i += 1
                    
                    if dep_line and not dep_line.startswith('#'):
                        # Поддерживаем зависимости через запятые
                        if ',' in dep_line:
                            dependencies = [dep.strip() for dep in dep_line.split(',')]
                        else:
                            dependencies = [dep_line]
                        
                        for dep in dependencies:
                            if dep:  # проверяем что зависимость не пустая
                                self._validate_uppercase_name(dep, i)
                                self.packages[current_package]['dependencies'].append({
                                    'name': dep,
                                    'version': '1.0.0'
                                })
            
            else:
                # Если строка не пустая, не комментарий и не пакет - ошибка формата
                if line and not line.startswith('#'):
                    raise ConfigError(f"Некорректный формат в строке {i}: {lines[i-1]}")
        
        print(f"[UPPERCASE] Загружено пакетов: {len(self.packages)}")
        for pkg_name, pkg_data in self.packages.items():
            deps = [dep['name'] for dep in pkg_data['dependencies']]
            print(f"  {pkg_name} -> {deps}")
    
    def _validate_uppercase_name(self, name: str, line_num: int):
        """Валидирует что имя пакета в UPPERCASE"""
        if not re.match(r'^[A-Z][A-Z0-9_]*$', name):
            raise ConfigError(
                f"Некорректное имя пакета в строке {line_num}: '{name}'. "
                f"Должно содержать только большие латинские буквы, цифры и подчеркивания"
            )
    
    def get_package(self, package_name: str, version: str = "latest") -> Optional[Dict[str, Any]]:
    
        if package_name in self.packages:
            pkg = self.packages[package_name]
            
            # ОТЛАДОЧНЫЙ ВЫВОД
            print(f"[UPPERCASE DEBUG] Пакет {package_name}: версия={pkg['version']}, зависимости={[dep['name'] for dep in pkg['dependencies']]}")
            
            # ПРАВИЛЬНЫЙ ФОРМАТ для dependency_analyzer
            return {
                "name": pkg["name"],
                "version": pkg["version"],
                "dependencies": {dep['name']: dep['version'] for dep in pkg['dependencies']}
            }
        print(f"[UPPERCASE DEBUG] Пакет {package_name} не найден!")
        return None
    
    def package_exists(self, package_name: str) -> bool:
        """Проверяет существование пакета"""
        return package_name in self.packages