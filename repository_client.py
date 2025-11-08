import json
import urllib.request
import urllib.error
import re
import socket
import os
from typing import Dict, Any
from network_error import NetworkError
import ssl

try:
    from test_data import get_test_package
    from test_repository import TestRepository
except ImportError:
    def get_test_package(package_name):
        return None
    
    class TestRepository:
        def __init__(self, repo_path: str = "./test-repo"):
            self.packages = {}
        
        def get_package(self, package_name: str, version: str = "latest"):
            return None
        
        def package_exists(self, package_name: str) -> bool:
            return False


class RepositoryClient:
    """Клиент для получения зависимостей из репозиториев"""
    
    def __init__(self):
        self.test_repo = None
        self.test_repo_path = None
    
    def init_test_repository(self, repo_path: str):
        """Инициализирует тестовый репозиторий"""
        # Нормализуем путь для сравнения
        normalized_repo_path = os.path.normpath(repo_path)
        # Инициализируем только если это новый путь или репозиторий еще не инициализирован
        if self.test_repo is None or self.test_repo_path != normalized_repo_path:
            print(f"Инициализация нового тестового репозитория: {repo_path}")
            self.test_repo_path = normalized_repo_path
            self.test_repo = TestRepository(repo_path)
        else:
            print(f"Использование существующего тестового репозитория: {self.test_repo_path}")
    
    @staticmethod
    def detect_repository_type(repo_url: str) -> str:
        """Определяет тип репозитория по URL"""
        # Проверяем локальные пути (НОВЫЙ КОД)
        # Сначала проверяем, не является ли это локальным путем
        # Проверяем относительные пути
        if repo_url.startswith('./') or repo_url.startswith('../'):
            return 'local'
        
        # Проверяем абсолютные пути или пути без протокола
        if not repo_url.startswith('http://') and not repo_url.startswith('https://'):
            # Если это путь с разделителями директорий или существующий путь
            if '/' in repo_url or '\\' in repo_url:
                # Нормализуем путь для проверки
                normalized_path = os.path.normpath(repo_url)
                if os.path.exists(normalized_path) or os.path.isdir(normalized_path):
                    return 'local'
                # Даже если путь не существует, но выглядит как локальный путь
                # Проверяем, что это не URL (нет двоеточия после первой части, или это Windows путь)
                if ':' not in repo_url or (len(repo_url) > 2 and repo_url[1:3] == ':\\'):  # Windows путь C:\
                    return 'local'
        
        # Проверяем удаленные репозитории
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
    def fetch_npm_package_info(package_name: str, version: str = "latest", test_mode: bool = False) -> Dict[str, Any]:
        """Получает информацию о NPM пакете с SSL фиксом"""
        
        if test_mode:
            test_data = get_test_package(package_name)
            if test_data:
                print(f"Используются тестовые данные для {package_name}")
                return test_data
            else:
                # Возвращаем тестовые данные даже если нет встроенных
                print(f"Используются данные по умолчанию для {package_name} (офлайн-режим)")
                return {
                    "name": package_name,
                    "version": version,
                    "dependencies": {
                        "accepts": "~1.3.8",
                        "body-parser": "1.20.1", 
                        "cookie": "0.5.0"
                    }
                }
        
        # Если test_mode=False, пытаемся сделать онлайн-запрос
        try:
            
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Формируем URL для запроса
            url = f"https://registry.npmjs.org/{package_name}"
            if version != "latest":
                url = f"https://registry.npmjs.org/{package_name}/{version}"
            
            print(f"Выполняется онлайн-запрос к: {url}")
            
            # Используем кастомный SSL контекст для HTTPS запроса
            request = urllib.request.Request(url)
            with urllib.request.urlopen(request, timeout=10, context=ssl_context) as response:
                # Читаем и парсим JSON ответ от npm registry
                data = json.loads(response.read().decode())
                return data
                
        except urllib.error.URLError as e:
            # Ошибки сети: нет интернета, DNS проблемы и т.д.
            raise NetworkError(f"Ошибка получения пакета {package_name}: {e}")
        except socket.timeout:
            # Таймаут соединения
            raise NetworkError(f"Таймаут при получении пакета {package_name}")
        except json.JSONDecodeError as e:
            # Ошибка парсинга JSON
            raise NetworkError(f"Ошибка парсинга ответа для {package_name}: {e}")
        except Exception as e:
            # Любые другие ошибки
            raise NetworkError(f"Неожиданная ошибка при получении {package_name}: {e}")
        
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
            # Для тестовых данных зависимости уже в правильном формате
            if 'dependencies' in package_info:
                deps = package_info.get('dependencies', {})
                for dep, version in deps.items():
                    dependencies[dep] = version
            else:
                # Для реальных NPM данных
                if 'dist-tags' in package_info and 'versions' in package_info:
                    latest_version = package_info['dist-tags']['latest']
                    version_data = package_info['versions'].get(latest_version, {})
                    
                    deps = version_data.get('dependencies', {})
                    for dep, version in deps.items():
                        dependencies[dep] = version
        
        elif repo_type == 'pypi':
            # Для PyPI зависимости находятся в 'info']['requires_dist'
            deps = package_info.get('info', {}).get('requires_dist', [])
            if deps:
                for dep in deps:
                    # Парсим строку типа "package>=1.0.0"
                    dep_name = re.split(r'[<>=!\[\];]', dep)[0].strip()
                    if dep_name and not dep_name.startswith('python_'):
                        dependencies[dep_name] = "latest"
        
        return dependencies
    
    