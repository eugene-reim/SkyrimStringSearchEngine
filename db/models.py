import sqlite3
from pathlib import Path
from typing import Optional
from .ats_parser import ATSParser
from rapidfuzz import fuzz


class TranslationDB:
    """База данных переводов с поддержкой неточного поиска и SQLite хранилищем"""

    def __init__(self, folder_path: str | Path, db_path: Optional[str | Path] = None):
        """
        Инициализация базы данных

        :param folder_path: Путь к папке с .ats файлами
        :param db_path: Путь к файлу БД (если None, используется in-memory БД)
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path if db_path else ":memory:")
        self._init_db()
        self.load_translations(folder_path)

    def _init_db(self):
        """Инициализация структуры БД"""
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS translations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original TEXT NOT NULL UNIQUE,
                    translated TEXT NOT NULL
                )
            """
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_original ON translations(original)"
            )

    def load_translations(self, folder_path: str | Path):
        """Загружает переводы из папки в БД"""
        folder_path = Path(folder_path) if isinstance(folder_path, str) else folder_path
        translations = ATSParser.load_from_folder(folder_path)

        with self.conn:
            for plugin_translations in translations.values():
                for string in plugin_translations:
                    if string.translated_string:
                        self.conn.execute(
                            "INSERT OR IGNORE INTO translations (original, translated) VALUES (?, ?)",
                            (string.original_string, string.translated_string),
                        )

    def search(self, query: str, threshold: int = 70) -> dict[str, str]:
        """
        Поиск перевода по запросу с учетом неточного совпадения

        :param query: Строка для поиска
        :param threshold: Порог совпадения (0-100)
        :return: Словарь {оригинал: перевод} с результатами поиска
        """
        results = {}
        cursor = self.conn.cursor()

        # Получаем все записи для поиска
        cursor.execute("SELECT original, translated FROM translations")
        for original, translation in cursor:
            # Нормализуем строки для поиска
            normalized_query = query.lower().replace("дракон", "dragon")
            normalized_original = original.lower()
            normalized_translation = translation.lower()

            # Ищем совпадения как в оригинале, так и в переводе
            ratio_original = fuzz.ratio(normalized_query, normalized_original)
            ratio_translated = fuzz.ratio(normalized_query, normalized_translation)

            # Берем максимальное совпадение
            ratio = max(ratio_original, ratio_translated)

            if ratio >= threshold:
                results[original] = translation

        return results

    def get_all(self) -> dict[str, str]:
        """Возвращает все доступные переводы"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT original, translated FROM translations")
        return dict(cursor.fetchall())

    def __del__(self):
        """Закрываем соединение при удалении объекта"""
        self.conn.close()
