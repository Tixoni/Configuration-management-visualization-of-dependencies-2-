import sys
import datetime


class OutputCapture:
    """Класс для захвата вывода в консоль и записи в файл"""
    
    def __init__(self, log_filename: str = "output_log.txt"):
        self.log_filename = log_filename
        self.original_stdout = sys.stdout
        self.log_file = None
    
    def start_capture(self):
        """Начать захват вывода"""
        self.log_file = open(self.log_filename, 'w', encoding='utf-8')
        
        class DualOutput:
            def __init__(self, original, log_file):
                self.original = original
                self.log_file = log_file
            
            def write(self, text):
                self.original.write(text)
                self.log_file.write(text)
                self.log_file.flush()
            
            def flush(self):
                self.original.flush()
                self.log_file.flush()
        
        sys.stdout = DualOutput(self.original_stdout, self.log_file)
        
        # Записываем заголовок в лог
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'='*60}")
        print(f"ЛОГ ВЫПОЛНЕНИЯ - {timestamp}")
        print(f"{'='*60}")
    
    def stop_capture(self):
        """Остановить захват вывода"""
        if self.log_file:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n{'='*60}")
            print(f"ВЫПОЛНЕНИЕ ЗАВЕРШЕНО - {timestamp}")
            print(f"{'='*60}")
            
            sys.stdout = self.original_stdout
            self.log_file.close()
            print(f"\nПолный лог выполнения сохранен в: {self.log_filename}")