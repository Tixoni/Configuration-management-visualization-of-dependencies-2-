from typing import Dict, Any, Set, Tuple
from repository_client import RepositoryClient
from network_error import NetworkError


class DependencyAnalyzer:
    """Анализатор зависимостей"""
    
    def __init__(self, max_depth: int = 3, filter_str: str = ""):
        self.max_depth = max_depth
        self.filter_str = filter_str
        self.visited_packages: Set[Tuple[str, str]] = set()
        self.dependency_tree: Dict[str, Any] = {}
        self.repository_client = RepositoryClient()
    
    def analyze_package(self, package_name: str, version: str = "latest", 
                   repo_url: str = "https://registry.npmjs.org", depth: int = 0, 
                   test_mode: bool = False) -> Dict[str, Any]:
    
    
        if depth >= self.max_depth:
            return {"name": package_name, "version": version, "dependencies": {}}
        
        cache_key = (package_name, version)
        if cache_key in self.visited_packages:
            return {"name": package_name, "version": version, "dependencies": {}, "cached": True}
        
        self.visited_packages.add(cache_key)
        
        try:
            print(f"Анализ {package_name}@{version} (уровень {depth})...")
            
            # Определяем тип репозитория
            repo_type = self.repository_client.detect_repository_type(repo_url)
            print(f"Определен тип репозитория для '{repo_url}': {repo_type}")
            
            # Получаем информацию о пакете (ОБНОВЛЕННЫЙ КОД)
            if repo_type == 'npm':
                package_info = self.repository_client.fetch_npm_package_info(
                    package_name, "latest", test_mode
                )
            elif repo_type == 'pypi':
                package_info = self.repository_client.fetch_pypi_package_info(package_name, version)
            elif repo_type == 'local':  # ← НОВАЯ ОБРАБОТКА ЛОКАЛЬНЫХ РЕПОЗИТОРИЕВ
                print(f"Обработка локального репозитория: {repo_url}")
                # Инициализируем тестовый репозиторий если еще не инициализирован
                if not self.repository_client.test_repo:
                    print(f"Инициализация тестового репозитория с путем: {repo_url}")
                    self.repository_client.init_test_repository(repo_url)
                else:
                    print(f"Тестовый репозиторий уже инициализирован")
                
                print(f"Поиск пакета '{package_name}' в локальном репозитории...")
                print(f"Загруженные пакеты: {list(self.repository_client.test_repo.packages.keys()) if self.repository_client.test_repo else 'репозиторий не инициализирован'}")
                package_info = self.repository_client.test_repo.get_package(package_name, version)
                if not package_info:
                    available_packages = list(self.repository_client.test_repo.packages.keys()) if self.repository_client.test_repo else []
                    raise NetworkError(
                        f"Пакет {package_name} не найден в локальном репозитории {repo_url}. "
                        f"Доступные пакеты: {', '.join(available_packages) if available_packages else 'нет'}"
                    )
            else:
                raise NetworkError(f"Неподдерживаемый репозиторий: {repo_url}")
            
            # Извлекаем зависимости
            dependencies = self.repository_client.extract_dependencies(package_info, repo_type)
            
            # Фильтруем зависимости если нужно
            if self.filter_str:
                dependencies = {k: v for k, v in dependencies.items() if self.filter_str in k}
            
            # Рекурсивно анализируем зависимости
            child_deps = {}
            for dep_name, dep_version in dependencies.items():
                try:
                    # Для локального репозитория сохраняем тип репозитория
                    # Для npm репозитория передаем test_mode дальше
                    child_deps[dep_name] = self.analyze_package(
                        dep_name, dep_version, repo_url, depth + 1, test_mode
                    )
                except (NetworkError, Exception) as e:
                    child_deps[dep_name] = {
                        "name": dep_name, 
                        "version": dep_version,
                        "error": str(e),
                        "dependencies": {}
                    }
            
            return {
                "name": package_name,
                "version": version,
                "dependencies": child_deps
            }
            
        except Exception as e:
            return {
                "name": package_name,
                "version": version,
                "error": str(e),
                "dependencies": {}
            }