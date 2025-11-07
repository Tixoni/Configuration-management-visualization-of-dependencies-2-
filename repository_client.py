import json
import urllib.request
import urllib.error
import re
import socket
from typing import Dict, Any
from network_error import NetworkError

try:
    from test_data import get_test_package
except ImportError:
    def get_test_package(package_name):
        return None


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
    def fetch_npm_package_info(package_name: str, version: str = "latest", test_mode: bool = False) -> Dict[str, Any]:
        """Получает информацию о NPM пакете"""
        
        # Если тестовый режим, используем ТОЛЬКО локальные данные
        if test_mode:
            test_data = get_test_package(package_name)
            if test_data:
                print(f"Используются тестовые данные для {package_name}")
                return test_data
            else:
                # В тестовом режиме возвращаем базовую структуру для неизвестных пакетов
                print(f"Тестовые данные для {package_name} не найдены")
                return {
                    "name": package_name,
                    "version": version,
                    "dependencies": {}
                }
        
        # Режим с интернетом (оригинальная логика)
        try:
            url = f"https://registry.npmjs.org/{package_name}"
            if version != "latest":
                url = f"https://registry.npmjs.org/{package_name}/{version}"
            
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                return data
        except Exception as e:
            raise NetworkError(f"Ошибка получения NPM пакета {package_name}: {e}")
    
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