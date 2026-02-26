# 🧰 TOOLBOX — Python / FastAPI

## ⚡ Быстрый старт

```bash
# 1. Создай виртуальное окружение (рекомендуется)
python -m venv venv
source venv/bin/activate      # Linux / Mac
venv\Scripts\activate         # Windows

# 2. Установи зависимости
pip install -r requirements.txt

# 3. Положи index.html в папку static/
#    (скачай toolbox.html из предыдущей версии и переименуй)

# 4. Запусти
uvicorn main:app --reload --port 3000

# Открой: http://localhost:3000
```

## 📖 Автодокументация API

FastAPI генерирует документацию автоматически:
- **Swagger UI**: http://localhost:3000/docs
- **ReDoc**:      http://localhost:3000/redoc

## 🔌 API Endpoints

| Метод | URL | Описание |
|---|---|---|
| GET | `/api/health` | Статус сервера |
| POST | `/api/hash` | MD5/SHA хэши (hashlib) |
| POST | `/api/diff` | Diff двух текстов (LCS) |
| POST | `/api/text/stats` | Статистика текста |
| POST | `/api/text/replace` | Найти и заменить (с RegEx) |
| POST | `/api/convert/json-csv` | JSON → CSV |
| POST | `/api/convert/csv-json` | CSV → JSON |
| POST | `/api/convert/file` | Загрузка файла |
| GET | `/api/snippets` | Список сниппетов |
| POST | `/api/snippets` | Создать сниппет |
| GET | `/api/snippets/{id}` | Получить сниппет |
| PUT | `/api/snippets/{id}` | Обновить сниппет |
| DELETE | `/api/snippets/{id}` | Удалить сниппет |

## 🗄 База данных

SQLite — файл `toolbox.db` создаётся автоматически при первом запуске.

## 🐍 Отличия от Node.js версии

| | Node.js (Express) | Python (FastAPI) |
|---|---|---|
| Хранение | In-memory | SQLite (персистентно!) |
| Хэши | Node crypto | hashlib (+ SHA3, BLAKE2!) |
| Документация | — | Swagger автоматически |
| Типизация | — | Pydantic модели |
| Перезагрузка | nodemon | uvicorn --reload |
| Дополнительный API | — | /api/text/stats, /api/text/replace |
