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
            print(f"[ANALYZE DEBUG] Тип репозитория '{repo_url}': {repo_type}")
            
            # Получаем информацию о пакете
            package_info = None
            actual_version = version
            
            try:
                if repo_type == 'npm':
                    package_info = self.repository_client.fetch_npm_package_info(
                        package_name, version, test_mode
                    )
                elif repo_type == 'pypi':
                    package_info = self.repository_client.fetch_pypi_package_info(package_name, version)
                    actual_version = package_info.get('version', version)
                elif repo_type == 'uppercase':
                    package_info = self.repository_client.fetch_uppercase_package_info(
                        package_name, version, repo_url
                    )
                    actual_version = package_info.get('version', version) if package_info else version
                elif repo_type == 'local':
                    pass
                else:
                    raise NetworkError(f"Неподдерживаемый репозиторий: {repo_url}")
                    
            except NetworkError as e:
                return {
                    "name": package_name,
                    "version": version,
                    "error": str(e),
                    "dependencies": {}
                }
            
            # Извлекаем зависимости (БЕЗ ФИЛЬТРАЦИИ на этом этапе)
            dependencies = self.repository_client.extract_dependencies(package_info, repo_type)
            
            # Рекурсивно анализируем зависимости (ВСЕГДА анализируем все зависимости)
            child_deps = {}
            for dep_name, dep_version in dependencies.items():
                try:
                    child_result = self.analyze_package(
                        dep_name, dep_version, repo_url, depth + 1, test_mode
                    )
                    # ФИЛЬТРАЦИЯ ПРИМЕНЯЕТСЯ ЗДЕСЬ: добавляем только если пакет или его дети прошли фильтр
                    if self._should_include_in_graph(child_result):
                        child_deps[dep_name] = child_result
                except (NetworkError, Exception) as e:
                    error_result = {
                        "name": dep_name, 
                        "version": dep_version,
                        "error": str(e),
                        "dependencies": {}
                    }
                    if self._should_include_in_graph(error_result):
                        child_deps[dep_name] = error_result
            
            result = {
                "name": package_name,
                "version": actual_version,
                "dependencies": child_deps
            }
            
            # Если у пакета нет детей после фильтрации, но сам пакет проходит фильтр - оставляем его
            if not child_deps and self.filter_str and self.filter_str in package_name:
                return result
            elif not child_deps and self.filter_str:
                # Пакет не проходит фильтр и у него нет подходящих детей - исключаем из графа
                return {"name": package_name, "version": actual_version, "dependencies": {}}
            else:
                return result
                
        except Exception as e:
            error_result = {
                "name": package_name,
                "version": version,
                "error": str(e),
                "dependencies": {}
            }
            if self._should_include_in_graph(error_result):
                return error_result
            else:
                return {"name": package_name, "version": version, "dependencies": {}}
        
    def _should_include_in_graph(self, package_data: Dict[str, Any]) -> bool:
        """Определяет, должен ли пакет быть включен в граф с учетом фильтра"""
        if not self.filter_str:
            return True
        
        # Проверяем сам пакет
        if self.filter_str in package_data.get('name', ''):
            return True
        
        # Рекурсивно проверяем детей
        for child_name, child_data in package_data.get('dependencies', {}).items():
            if self._should_include_in_graph(child_data):
                return True
        
        return False