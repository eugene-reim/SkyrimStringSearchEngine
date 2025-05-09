# 🏰 Skyrim String Search Engine
[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.68+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](https://opensource.org/licenses/MIT)

**Инструмент для поиска по файлам перевода Skyrim**  
🔍 Поиск переводов | 📚 База данных строк | 🚀 API интерфейс

## ✨ Основные возможности

- 🔎 **Умный поиск** с поддержкой кириллицы и приоритетом коротких строк
- 🗃️ **База данных** всех игровых строк и их переводов
- 🌐 **REST API** для интеграции с другими инструментами
- 📊 **Логирование** всех операций
- ⚡ **Высокая производительность** благодаря SQLite и FastAPI

## 🛠 Технологии

![Python](https://img.shields.io/badge/-Python-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/-FastAPI-009688?logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/-SQLite-003B57?logo=sqlite&logoColor=white)
![Pydantic](https://img.shields.io/badge/-Pydantic-920000?logo=pydantic&logoColor=white)

## 🚀 Быстрый старт

```bash
# Клонировать репозиторий
git clone https://github.com/your-repo/skyrim-translator.git

# Установить зависимости
pip install -r requirements.txt

# Запустить сервер
python main.py
```

Сервер будет доступен по адресу: [http://localhost:8000](http://localhost:8000)

## 📚 API Документация

После запуска сервера документация API доступна по адресам:
- Swagger UI: [/docs](http://localhost:8000/docs)
- ReDoc: [/redoc](http://localhost:8000/redoc)

## 🎯 Особенности поиска

```python
# Пример поиска
GET /api/v1/search?query=дракон&case_insensitive=true
```

✅ Поддержка кириллицы  
✅ Приоритет коротких строк  
✅ Регистронезависимый поиск  
✅ Фильтрация по оригиналу/переводу

## 📦 Структура проекта

```
skyrim-translator/
├── api/           # API эндпоинты
├── core/          # Основная логика
├── db/            # Работа с базой данных
├── skyrim_strings # Игровые строки
├── static/        # Статические файлы
└── tests/         # Тесты
```

## 🤝 Участие в разработке

1. Форкните репозиторий
2. Создайте ветку для вашей фичи (`git checkout -b feature/amazing-feature`)
3. Сделайте коммит изменений (`git commit -m 'Add some amazing feature'`)
4. Запушьте в ветку (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## 📜 Лицензия

MIT © 2025 Skyrim Translator Team
