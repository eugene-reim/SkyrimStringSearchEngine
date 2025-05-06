import sqlite3
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import asdict
from skyrim_translator.core.parser import String


class DBHandler:
    def __init__(self, db_path: str = "database/translations.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None

    def __enter__(self):
        if not hasattr(self, "conn") or self.conn is None:
            self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Не закрываем соединение, чтобы оно оставалось доступным
        pass

    def connect(self):
        self.conn = sqlite3.connect(self.db_path)
        # Устанавливаем кодировку UTF-8
        self.conn.execute("PRAGMA encoding = 'UTF-8'")
        self._create_tables()

    def close(self):
        if self.conn:
            self.conn.close()

    def _create_tables(self):
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS translations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plugin_name TEXT NOT NULL,
                    editor_id TEXT,
                    form_id TEXT,
                    string_index INTEGER,
                    type TEXT NOT NULL,
                    original_string TEXT NOT NULL,
                    translated_string TEXT,
                    status TEXT NOT NULL
                )
            """
            )
            self.conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_plugin_name 
                ON translations (plugin_name)
            """
            )

    def save_translations(self, plugin_name: str, strings: List[String]):
        with self.conn:
            for string in strings:
                data = asdict(string)
                data["plugin_name"] = plugin_name
                data["status"] = string.status.name
                data["string_index"] = string.index  # Добавляем string_index

                # Нормализуем и приводим строки к UTF-8
                import unicodedata

                def normalize_str(s):
                    if not s:
                        return s
                    if not isinstance(s, str):
                        s = str(s)
                    return unicodedata.normalize(
                        "NFKC", s.encode("utf-8").decode("utf-8")
                    )

                for key in ["original_string", "translated_string"]:
                    data[key] = normalize_str(data[key])

                self.conn.execute(
                    """
                    INSERT INTO translations 
                    (plugin_name, editor_id, form_id, string_index, type, 
                     original_string, translated_string, status)
                    VALUES 
                    (:plugin_name, :editor_id, :form_id, :string_index, :type, 
                     :original_string, :translated_string, :status)
                """,
                    data,
                )

    def get_translations(self, plugin_name: str) -> List[Dict]:
        with self.conn:
            cursor = self.conn.execute(
                """
                SELECT editor_id, form_id, string_index, type, 
                       original_string, translated_string, status
                FROM translations
                WHERE plugin_name = ?
            """,
                (plugin_name,),
            )
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def translation_exists(self, plugin_name: str) -> bool:
        with self.conn:
            cursor = self.conn.execute(
                """
                SELECT 1 FROM translations 
                WHERE plugin_name = ? 
                LIMIT 1
            """,
                (plugin_name,),
            )
            return cursor.fetchone() is not None

    def clear_database(self):
        """Очищает таблицу translations"""
        with self.conn:
            self.conn.execute("DELETE FROM translations")
