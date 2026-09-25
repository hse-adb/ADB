## Dynamically served website / Динамичный сайт
Установка зависимостей:
```bash
pip install -e .
```
Запуск:
```bash
clld initdb --cldf .\ADB\data\metadata.json "development.ini"
pserve --reload development.ini
```
Сайт доступен до тех пор пока 

## Static website / Статичный сайт

### Компиляция сайта
Установка зависимостей:
```bash
pip install -r scripts\static_requirements.txt
python3 -m playwright install chromium
```
Запуск компиляции:
```bash
python3 scripts/build_static.py
```
Обратите внимание: компиляция большого количества страниц это очень длительный процесс &mdash; закладывайте на отработку скрипта много времени

Скомпилированный сайт будет сохранён в папке `static-site`

### Тестирование сайта
```bash
cd static-site
python3 -m http.server 8000
```
Сайт станет доступен по адресу `localhost:8000`. `8000` во второй команде можно заменить на произвольный порт. Статичный сайт можно сохранить в репозитории GitHub и хостить через GitHub Pages
