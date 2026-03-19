Install dependencies: / Установка зависимостей:
```bash
pip install -e .
```

Run: / Запуск:
```bash
clld initdb --cldf .\ADB\data\metadata.json "development.ini"
pserve --reload development.ini
```
