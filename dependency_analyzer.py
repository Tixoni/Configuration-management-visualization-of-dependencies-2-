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
    
    def analyze_package(self, package_name: str, version: str = "latest", 
                       repo_url: str = "https://registry.npmjs.org", depth: int = 0, 
                       test_mode: bool = False) -> Dict[str, Any]:
        """Рекурсивно анализирует зависимости пакета"""
        
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
                package_info = RepositoryClient.fetch_npm_package_info(package_name, "latest", test_mode)
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
                    # ОШИБКА БЫЛА ЗДЕСЬ: передаем dep_version вместо "latest"
                    child_deps[dep_name] = self.analyze_package(
                        dep_name, dep_version, repo_url, depth + 1, test_mode  # ← ИСПРАВЛЕНО: dep_version вместо "latest"
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
                "version": version,  # Сохраняем версию, которую передали в метод
                "dependencies": child_deps
            }
            
        except Exception as e:
            return {
                "name": package_name,
                "version": version,
                "error": str(e),
                "dependencies": {}
            }