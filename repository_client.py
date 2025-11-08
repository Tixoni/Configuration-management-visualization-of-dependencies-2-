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

    @staticmethod
    def _normalize_package_name(name: str) -> str:
        """Нормализует имя пакета (заменяет дефисы на подчеркивания)"""
        if not name:
            return name
        
        # Заменяем дефисы на подчеркивания
        name = name.replace('-', '_')
        
        # Удаляем лишние символы в конце
        name = re.sub(r'[^\w\.]+$', '', name)
        
        return name.lower()

    @staticmethod
    def _normalize_python_version(requested_version: str, available_versions: list) -> str:
        """Нормализует запрошенную версию на основе доступных версий"""
        if not available_versions:
            return "latest"
        
        # Если запрошенная версия существует - возвращаем её
        if requested_version in available_versions:
            return requested_version
        
        # Пытаемся найти подходящую версию
        requested_clean = re.sub(r'[^\d\.]', '', requested_version)
        
        if not requested_clean:
            return available_versions[-1]  # возвращаем последнюю версию
        
        # Ищем версии, которые начинаются с запрошенной
        for available in available_versions:
            if available.startswith(requested_clean):
                return available
        
        # Ищем версии, содержащие запрошенную
        for available in available_versions:
            if requested_clean in available:
                return available
        
        # Возвращаем последнюю доступную версию
        return available_versions[-1]

    @staticmethod
    def _extract_python_version(dep_string: str) -> str:
        """Извлекает версию из строки зависимости Python"""
        if not dep_string:
            return "latest"
        
        # Удаляем условные зависимости (всё что после ;)
        dep_string = dep_string.split(';')[0].strip()
        
        # Ищем версионные спецификаторы - ТОЛЬКО КОРРЕКТНЫЕ ФОРМАТЫ
        version_patterns = [
            r'===?\s*([\d\.]+[\w]*)',     # ==, === (только цифры и точки)
            r'>=\s*([\d\.]+)',            # >= (только цифры)
            r'<=\s*([\d\.]+)',            # <= (только цифры)  
            r'>\s*([\d\.]+)',             # > (только цифры)
            r'<\s*([\d\.]+)',             # < (только цифры)
            r'~=\s*([\d\.]+)',            # ~= (только цифры)
            r'!=\s*([\d\.]+)',            # != (только цифры)
        ]
        
        for pattern in version_patterns:
            match = re.search(pattern, dep_string)
            if match:
                version = match.group(1)
                version = version.strip('"\'').strip()
                # Проверяем что версия содержит хотя бы одну цифру
                if version and re.search(r'\d', version):
                    return version
        
        # Если версия не указана явно, возвращаем latest
        return "latest"

    @staticmethod
    def fetch_pypi_package_info(package_name: str, version: str = "latest") -> Dict[str, Any]:
        """Получает информацию о Python пакете с улучшенной обработкой версий"""
        try:
            url = f"https://pypi.org/pypi/{package_name}/json"
            
            # SSL контекст для обхода проблем с сертификатами
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            request = urllib.request.Request(url)
            with urllib.request.urlopen(request, timeout=10, context=ssl_context) as response:
                data = json.loads(response.read().decode())
                
                # УЛУЧШЕННОЕ определение версии
                if version == "latest":
                    version = data['info']['version']
                    print(f"Используется последняя версия: {version}")
                else:
                    # НОРМАЛИЗАЦИЯ ВЕРСИИ - исправляем неправильные версии
                    available_versions = list(data['releases'].keys())
                    normalized_version = RepositoryClient._normalize_python_version(version, available_versions)
                    if normalized_version != version:
                        print(f"Версия {version} нормализована до {normalized_version}")
                        version = normalized_version
                    
                    # Проверяем существование версии
                    if version not in data['releases']:
                        available_versions = list(data['releases'].keys())[:5]
                        raise NetworkError(
                            f"Версия {version} не найдена для пакета {package_name}. "
                            f"Доступные версии: {', '.join(available_versions)}"
                        )
                
                return {
                    'info': data['info'],
                    'version': version,
                    'releases': data['releases'],
                    'dependencies': data['info'].get('requires_dist', [])
                }
                
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
            # УЛУЧШЕННАЯ обработка PyPI зависимостей
            deps_list = package_info.get('dependencies') or package_info.get('info', {}).get('requires_dist', [])
            
            if deps_list:
                print(f"Обработка зависимостей PyPI:")
                for dep in deps_list:
                    try:
                        dep_clean = dep.split(';')[0].strip()
                        # УЛУЧШЕННЫЙ парсинг имени пакета
                        dep_name_match = re.match(r'^([a-zA-Z0-9_\-\.]+)', dep_clean)
                        if not dep_name_match:
                            continue
                        
                        dep_name = dep_name_match.group(1).strip()
                        
                        # Нормализуем имя пакета (убираем неправильные символы)
                        dep_name = RepositoryClient._normalize_package_name(dep_name)
                        
                        # ФИЛЬТР неправильных имен
                        if (dep_name and 
                            not dep_name.startswith('python') and 
                            not dep_name.startswith('extra') and
                            len(dep_name) > 1 and  # не слишком короткое
                            not re.search(r'[~!@#$%^&*()+=]', dep_name) and  # нет спецсимволов
                            dep_name not in ['', 'None', 'None)', 'or']):
                            
                            version = RepositoryClient._extract_python_version(dep)
                            dependencies[dep_name] = version
                            print(f"  - {dep_name} -> {version}")
                            
                    except Exception as e:
                        print(f"  Ошибка парсинга '{dep}': {e}")
            
            if not dependencies:
                print(f"  Зависимости не найдены")
        
        return dependencies

    def init_test_repository(self, repo_path: str):
        """Инициализирует тестовый репозиторий"""
        normalized_repo_path = os.path.normpath(repo_path)
        if self.test_repo is None or self.test_repo_path != normalized_repo_path:
            print(f"Инициализация нового тестового репозитория: {repo_path}")
            self.test_repo_path = normalized_repo_path
            self.test_repo = TestRepository(repo_path)
        else:
            print(f"Использование существующего тестового репозитория: {self.test_repo_path}")

    @staticmethod
    def detect_repository_type(repo_url: str) -> str:
        """Определяет тип репозитория по URL"""
        if repo_url.startswith('./') or repo_url.startswith('../'):
            return 'local'
        
        if not repo_url.startswith('http://') and not repo_url.startswith('https://'):
            if '/' in repo_url or '\\' in repo_url:
                normalized_path = os.path.normpath(repo_url)
                if os.path.exists(normalized_path) or os.path.isdir(normalized_path):
                    return 'local'
                if ':' not in repo_url or (len(repo_url) > 2 and repo_url[1:3] == ':\\'):
                    return 'local'
        
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
        """Получает информацию о NPM пакете с исправленным URL"""
        
        if test_mode:
            test_data = get_test_package(package_name)
            if test_data:
                print(f"Используются тестовые данные для {package_name}")
                return test_data
            else:
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
        
        try:
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # ИСПРАВЛЕНИЕ: Всегда запрашиваем основной URL пакета без версии
            # NPM registry возвращает всю информацию о пакете, включая все версии
            url = f"https://registry.npmjs.org/{package_name}"
            
            print(f"Выполняется онлайн-запрос к: {url}")
            
            request = urllib.request.Request(url)
            with urllib.request.urlopen(request, timeout=10, context=ssl_context) as response:
                data = json.loads(response.read().decode())
                
                # После получения данных, извлекаем информацию о нужной версии
                if version != "latest" and version in data.get('versions', {}):
                    # Если указана конкретная версия и она существует
                    version_data = data['versions'][version]
                    return {
                        "name": data.get('name', package_name),
                        "version": version,
                        "dependencies": version_data.get('dependencies', {})
                    }
                else:
                    # Используем последнюю версию (по умолчанию)
                    latest_version = data.get('dist-tags', {}).get('latest')
                    if latest_version and latest_version in data.get('versions', {}):
                        version_data = data['versions'][latest_version]
                        return {
                            "name": data.get('name', package_name),
                            "version": latest_version,
                            "dependencies": version_data.get('dependencies', {})
                        }
                    else:
                        # Если не удалось найти последнюю версию, возвращаем базовую информацию
                        return {
                            "name": data.get('name', package_name),
                            "version": version,
                            "dependencies": data.get('versions', {}).get(list(data['versions'].keys())[0], {}).get('dependencies', {})
                        }
                    
        except urllib.error.URLError as e:
            raise NetworkError(f"Ошибка получения пакета {package_name}: {e}")
        except socket.timeout:
            raise NetworkError(f"Таймаут при получении пакета {package_name}")
        except json.JSONDecodeError as e:
            raise NetworkError(f"Ошибка парсинга ответа для {package_name}: {e}")
        except Exception as e:
            raise NetworkError(f"Неожиданная ошибка при получении {package_name}: {e}")