import re
from typing import Dict, Any
from config_error import ConfigError


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