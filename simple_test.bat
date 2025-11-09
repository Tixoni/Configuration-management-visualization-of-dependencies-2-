@echo off
chcp 65001 >nul
echo ================================
echo ПРОСТОЙ ТЕСТ ВИЗУАЛИЗАТОРА
echo ================================
echo.

echo Создание тестовых UPPERCASE репозиториев...
(
echo # Тестовый репозиторий с пакетами в UPPERCASE
echo PACKAGEA
echo     PACKAGEB
echo     PACKAGEC
echo PACKAGEB
echo     PACKAGED
echo     PACKAGEE
echo PACKAGEC
echo     PACKAGEF
echo PACKAGED
echo     PACKAGEG
echo PACKAGEE
echo PACKAGEF
echo PACKAGEG
) > test_uppercase_repo.txt

(
echo # Репозиторий с циклическими зависимостями для тестирования
echo PACKAGEX
echo     PACKAGEY
echo PACKAGEY
echo     PACKAGEZ
echo PACKAGEZ
echo     PACKAGEX
) > test_uppercase_repo_cyclic.txt

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

echo ТЕСТ 5: UPPERCASE репозиторий (специальный формат)
echo.
(
echo package_name: PACKAGEA
echo repository_url: test_uppercase_repo.txt
echo test_repository_mode: false
echo package_version: latest
echo output_filename: test5_uppercase.txt
echo ascii_tree_output: true
echo max_depth: 3
echo filter_substring: ""
) > test5.yaml

python main.py test5.yaml
if %errorlevel% equ 0 (
    echo ТЕСТ 5 ПРОЙДЕН: UPPERCASE репозиторий работает
) else (
    echo ТЕСТ 5 НЕ ПРОЙДЕН: UPPERCASE репозиторий
)
echo.

echo ТЕСТ 6: UPPERCASE репозиторий с циклическими зависимостями
echo.
(
echo package_name: PACKAGEX
echo repository_url: test_uppercase_repo_cyclic.txt
echo test_repository_mode: false
echo package_version: latest
echo output_filename: test6_uppercase_cyclic.txt
echo ascii_tree_output: true
echo max_depth: 5
echo filter_substring: ""
) > test6.yaml

python main.py test6.yaml
if %errorlevel% equ 0 (
    echo ТЕСТ 6 ПРОЙДЕН: Циклические зависимости обработаны
) else (
    echo ТЕСТ 6 НЕ ПРОЙДЕН: Циклические зависимости
)
echo.

echo ТЕСТ 7: Фильтрация в UPPERCASE репозитории
echo.
(
echo package_name: PACKAGEA
echo repository_url: test_uppercase_repo.txt
echo test_repository_mode: false
echo package_version: latest
echo output_filename: test7_uppercase_filtered.txt
echo ascii_tree_output: true
echo max_depth: 3
echo filter_substring: "PACKAGEE"
) > test7.yaml

python main.py test7.yaml
if %errorlevel% equ 0 (
    echo ТЕСТ 7 ПРОЙДЕН: Фильтрация в UPPERCASE работает
) else (
    echo ТЕСТ 7 НЕ ПРОЙДЕН: Фильтрация в UPPERCASE
)
echo.

echo Очистка временных файлов...
del test1.yaml 2>nul
del test2.yaml 2>nul
del test3.yaml 2>nul
del test4.yaml 2>nul
del test5.yaml 2>nul
del test6.yaml 2>nul
del test7.yaml 2>nul

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