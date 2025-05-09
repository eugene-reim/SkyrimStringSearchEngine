import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from dataclasses import asdict
from core.models.string import String
from enum import Enum


class DBHandler:
    """Основной класс для работы с базой данных переводов.

    Отвечает за:
    - Создание/подключение к SQLite базе данных
    - Управление структурой таблиц и индексов
    - Сохранение и поиск переводов
    - Обеспечение целостности данных

    Атрибуты:
        db_path (str): Путь к файлу базы данных
        _conn (sqlite3.Connection): Соединение с базой данных
        logger (logging.Logger): Логгер для записи событий
    """

    def __init__(self, db_path: str = "database/translations.db"):
        """Инициализация обработчика базы данных.

        Args:
            db_path (str): Путь к файлу базы данных. По умолчанию 'database/translations.db'
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = None
        from core.logger import get_logger

        self.logger = get_logger(__name__)

    @property
    def conn(self):
        """Автоматически устанавливает соединение при первом обращении"""
        if self._conn is None:
            self.connect()
        return self._conn

    @conn.setter
    def conn(self, value):
        self._conn = value

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Не закрываем соединение, чтобы оно оставалось доступным
        pass

    def connect(self):
        self._conn = sqlite3.connect(self.db_path)
        # Устанавливаем параметры для уменьшения блокировок
        self._conn.execute("PRAGMA encoding = 'UTF-8'")
        self._conn.execute("PRAGMA journal_mode = WAL")  # Режим записи журнала
        self._conn.execute(
            "PRAGMA synchronous = NORMAL"
        )  # Баланс между надежностью и скоростью
        self._conn.execute(
            "PRAGMA busy_timeout = 5000"
        )  # Таймаут ожидания блокировки 5 секунд
        self._create_tables()

    def close(self):
        if self.conn:
            self.conn.close()

    def _create_tables(self):
        try:
            # Создаем основную таблицу translations
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS translations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plugin_name TEXT NOT NULL,
                    original_string TEXT NOT NULL,
                    translated_string TEXT
                )
            """
            )
            self.conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_plugin_name 
                ON translations (plugin_name)
            """
            )
            # Добавляем индексы для поиска
            self.conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_original_string 
                ON translations (original_string)
            """
            )
            self.conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_translated_string 
                ON translations (translated_string)
            """
            )
        except sqlite3.OperationalError as e:
            if "locked" in str(e):
                self.logger.warning("Database is locked, retrying...")
                import time

                time.sleep(1)
                return self._create_tables()  # Рекурсивный повтор
            self.logger.error(f"Database error in _create_tables: {e}")
            raise
        except sqlite3.Error as e:
            self.logger.error(f"Database error in _create_tables: {e}")
            raise

    def save_translations(self, plugin_name: str, strings: Dict[int, Tuple[str, str]]):
        """Сохраняет строки перевода в базу данных"""
        if not strings:
            self.logger.warning("No strings to save!")
            return 0

        try:
            if not self.conn:
                self.connect()

            existing_count = self.conn.execute(
                "SELECT COUNT(*) FROM translations"
            ).fetchone()[0]
            self.logger.info(f"Saving {len(strings)} strings for plugin: {plugin_name}")

            data_list = []
            for _, (original, translated) in strings.items():
                data_list.append(
                    {
                        "plugin_name": plugin_name,
                        "original_string": original,
                        "translated_string": translated,
                    }
                )

            with self.conn:
                self.conn.executemany(
                    """INSERT OR IGNORE INTO translations 
                    (plugin_name, original_string, translated_string)
                    VALUES 
                    (:plugin_name, :original_string, :translated_string)""",
                    data_list,
                )

                new_count = self.conn.execute(
                    "SELECT COUNT(*) FROM translations"
                ).fetchone()[0]
                added = new_count - existing_count
                self.logger.info(f"Added {added} new records")
                return added

        except sqlite3.Error as e:
            self.logger.error(f"Database error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error saving translations: {e}")
            raise

    def get_translations(self, plugin_name: str) -> List[Dict]:
        with self.conn:
            cursor = self.conn.execute(
                """
                SELECT plugin_name, original_string, translated_string
                FROM translations
                WHERE plugin_name = ?
            """,
                (plugin_name,),
            )
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def translation_exists(self, plugin_name: str) -> bool:
        """Проверяет, есть ли записи в базе (игнорируя plugin_name)"""
        try:
            if not hasattr(self, "conn") or self.conn is None:
                self.connect()

            cursor = self.conn.execute("SELECT COUNT(*) FROM translations")
            count = cursor.fetchone()[0]
            self.logger.debug(f"Database record count: {count}")
            return count > 0

        except sqlite3.Error as e:
            self.logger.error(f"Database error in translation_exists: {e}")
            return False

    def clear_database(self):
        """Очищает таблицу translations"""
        with self.conn:
            self.conn.execute("DELETE FROM translations")

    def is_database_empty(self) -> bool:
        """Проверяет, пустая ли база данных"""
        if not hasattr(self, "conn") or self.conn is None:
            self.connect()
        cursor = self.conn.execute("SELECT 1 FROM translations LIMIT 1")
        return cursor.fetchone() is None

    def normalize_search(self, s: str) -> str:
        """Нормализует строку для поиска (NFKC + casefold)"""
        import unicodedata

        if not s:
            return ""
        return unicodedata.normalize("NFKC", s).casefold()

    def _register_unicode_functions(self):
        """Регистрирует функции для работы с Unicode в SQLite"""
        import unicodedata

        def normalize_compare(a: str, b: str) -> bool:
            """Сравнение строк с нормализацией Unicode и без учета регистра"""

            def prepare(s):
                if not s:
                    return ""
                return unicodedata.normalize("NFKC", s).casefold()

            return prepare(a) == prepare(b)

        def normalize_search(s: str) -> str:
            """Нормализация строки для поиска"""
            if not s:
                return ""
            return unicodedata.normalize("NFKC", s).casefold()

        self.conn.create_function("unicode_compare", 2, normalize_compare)
        self.conn.create_function("unicode_search", 1, normalize_search)

    def search_translations(
        self,
        search_query: str,
        search_in_original: bool = True,
        search_in_translated: bool = True,
        case_insensitive: bool = True,
        offset: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Dict], int, int]:
        """
        Ищет переводы по запросу в базе данных с поддержкой Unicode
        """
        if not hasattr(self, "conn") or self.conn is None:
            self.connect()

        self._register_unicode_functions()

        conditions = []
        params = []

        search_norm = (
            self.normalize_search(search_query) if case_insensitive else search_query
        )

        if search_in_original:
            if case_insensitive:
                conditions.append(
                    "unicode_search(original_string) LIKE unicode_search(?)"
                )
            else:
                conditions.append("original_string LIKE ?")
            params.append(f"%{search_query}%")

        if search_in_translated:
            if case_insensitive:
                conditions.append(
                    "unicode_search(translated_string) LIKE unicode_search(?)"
                )
            else:
                conditions.append("translated_string LIKE ?")
            params.append(f"%{search_query}%")

        if not conditions:
            return []

        where_clause = " OR ".join(conditions)

        query = f"""
            SELECT plugin_name, original_string, translated_string,
                   LENGTH(original_string) as original_length,
                   CASE 
                       WHEN original_string LIKE ? ESCAPE '\\' THEN 0
                       WHEN translated_string LIKE ? ESCAPE '\\' THEN 1
                       ELSE 2
                   END as match_priority
            FROM translations
            WHERE {where_clause}
            ORDER BY 
                match_priority ASC,
                LENGTH(original_string) ASC,
                CASE WHEN translated_string IS NOT NULL THEN 0 ELSE 1 END
            LIMIT ? OFFSET ?
        """
        # Добавляем параметры для match_priority и пагинации
        params.insert(0, f"%{search_query}%")
        params.insert(1, f"%{search_query}%")
        params.append(limit)
        params.append(offset)

        # Получаем результаты поиска
        cursor = self.conn.execute(query, params)
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        # Получаем общее количество совпадений
        count_query = f"SELECT COUNT(*) FROM translations WHERE {where_clause}"
        # Используем только параметры поиска, без параметров пагинации и match_priority
        count_params = params[2:-2] if len(params) > 4 else params[2:]
        total_matches = self.conn.execute(count_query, count_params).fetchone()[0]

        # Получаем общее количество строк в базе
        total_in_db = self.conn.execute("SELECT COUNT(*) FROM translations").fetchone()[
            0
        ]

        return results, total_matches, total_in_db
