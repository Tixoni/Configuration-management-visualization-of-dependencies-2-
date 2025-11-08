@echo off
chcp 65001 >nul
echo ================================
echo ПРОСТОЙ ТЕСТ ВИЗУАЛИЗАТОРА
echo ================================
echo.


echo.
echo ТЕСТ 1: Офлайн-режим (встроенные данные)
echo.
(
echo package_name: express
echo repository_url: https://registry.npmjs.org
echo test_repository_mode: true
echo package_version: latest
echo output_filename: test1_offline.txt
echo ascii_tree_output: true
echo max_depth: 2
echo filter_substring: ""
) > test1.yaml

python main.py test1.yaml
if %errorlevel% equ 0 (
    echo ТЕСТ 1 ПРОЙДЕН: Офлайн-режим работает
) else (
    echo ТЕСТ 1 НЕ ПРОЙДЕН: Офлайн-режим
)
echo.

echo ТЕСТ 2: Онлайн-режим (требует интернет)
echo.
(
echo package_name: express
echo repository_url: https://registry.npmjs.org
echo test_repository_mode: false
echo package_version: latest
echo output_filename: test2_online.txt
echo ascii_tree_output: true
echo max_depth: 3
echo filter_substring: ""
) > test2.yaml

python main.py test2.yaml
if %errorlevel% equ 0 (
    echo ТЕСТ 2 ПРОЙДЕН: Онлайн-режим работает
) else (
    echo ТЕСТ 2 НЕ ПРОЙДЕН: Онлайн-режим (возможно нет интернета)
)
echo.

echo ТЕСТ 3: Фильтрация пакетов
echo.
(
echo package_name: express
echo repository_url: https://registry.npmjs.org
echo test_repository_mode: false
echo package_version: latest
echo output_filename: test3_filtered.txt
echo ascii_tree_output: true
echo max_depth: 2
echo filter_substring: "cookie"
) > test3.yaml

python main.py test3.yaml
if %errorlevel% equ 0 (
    echo ТЕСТ 3 ПРОЙДЕН: Фильтрация работает
) else (
    echo ТЕСТ 3 НЕ ПРОЙДЕН: Фильтрация
)
echo.

echo ТЕСТ 4: Python пакет в онлайн-режиме (требует интернет)
echo.
(
echo package_name: requests
echo repository_url: https://pypi.org/pypi
echo test_repository_mode: false
echo package_version: latest
echo output_filename: test4_python.txt
echo ascii_tree_output: true
echo max_depth: 2
echo filter_substring: ""
) > test4.yaml

python main.py test4.yaml
if %errorlevel% equ 0 (
    echo ТЕСТ 4 ПРОЙДЕН: Python пакет работает
) else (
    echo ТЕСТ 4 НЕ ПРОЙДЕН: Python пакет (возможно нет интернета)
)
echo.

echo Очистка временных файлов...
del test1.yaml 2>nul
del test2.yaml 2>nul
del test3.yaml 2>nul
del test4.yaml 2>nul


echo.
echo ================================
echo РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ
echo ================================
echo.
echo Созданные файлы:
dir /b test*.txt 2>nul
echo.
echo Если тесты 2 или 4 не прошли - проверьте интернет-соединение
echo Простое тестирование завершено!
echo.

pause