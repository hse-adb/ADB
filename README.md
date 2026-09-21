Install dependencies: / Установка зависимостей:
```bash
pip install -e .
```

Run: / Запуск:
```bash
clld initdb --cldf .\ADB\data\metadata.json "development.ini"
pserve --reload development.ini
```

Static website compilation: / Компиляция статичного сайта:
```bash
pip install -r scripts\static_requirements.txt
python3 -m playwright install chromium
```
