"""
ATS Parser - модуль для работы с .ats файлами локализации
"""

import pickle
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path


@dataclass
class String:
    """
    Класс для хранения строк перевода
    """

    editor_id: str | None
    form_id: str | None
    index: int | None
    type: str
    original_string: str
    translated_string: str | None = None

    class Status(Enum):
        NoTranslationRequired = auto()
        TranslationComplete = auto()
        TranslationIncomplete = auto()
        TranslationRequired = auto()

    status: Status = None

    @classmethod
    def from_string_data(cls, string_data: dict[str, str]) -> "String":
        if "original" in string_data:
            status_name = string_data.get("status")
            try:
                status = cls.Status[status_name]
            except KeyError:
                status = cls.Status.TranslationComplete

            editor_id = string_data.get("editor_id")
            form_id = string_data.get("form_id")
            if editor_id and not form_id:
                if editor_id.startswith("[") and editor_id.endswith("]"):
                    form_id = editor_id
                    editor_id = None

            return String(
                editor_id=editor_id,
                form_id=form_id,
                index=string_data.get("index"),
                type=string_data["type"],
                original_string=string_data["original"],
                translated_string=string_data["string"],
                status=status,
            )

        else:
            status_name = string_data.get("status")
            try:
                status = cls.Status[status_name]
            except KeyError:
                status = cls.Status.TranslationRequired

            editor_id = string_data.get("editor_id")
            form_id = string_data.get("form_id")
            if editor_id and not form_id:
                if editor_id.startswith("[") and editor_id.endswith("]"):
                    form_id = editor_id
                    editor_id = None

            return String(
                editor_id=editor_id,
                form_id=form_id,
                index=string_data.get("index"),
                type=string_data["type"],
                original_string=string_data.get("string", ""),
                status=status,
            )

    def to_string_data(self) -> dict[str, str]:
        if self.translated_string is not None:
            return {
                "editor_id": self.editor_id,
                "form_id": self.form_id,
                "index": self.index,
                "type": self.type,
                "original": self.original_string,
                "string": self.translated_string,
                "status": self.status.name,
            }
        else:
            return {
                "editor_id": self.editor_id,
                "form_id": self.form_id,
                "index": self.index,
                "type": self.type,
                "string": self.original_string,
                "status": self.status.name,
            }


class ATSParser:
    """
    Класс для работы с .ats файлами и базой данных переводов
    """

    def __init__(self):
        from skyrim_translator.db.handler import DBHandler

        self.db = DBHandler()
        # Убедимся, что соединение с базой данных установлено
        if not hasattr(self.db, "conn") or self.db.conn is None:
            self.db.connect()

        # Проверяем, есть ли данные в базе
        with self.db:
            cursor = self.db.conn.execute("SELECT 1 FROM translations LIMIT 1")
            if not cursor.fetchone():
                print("База данных пуста, начинаем загрузку переводов")
                self.load_from_folder("skyrim_strings/russian")

    @staticmethod
    def load_ats(file_path: str | Path) -> list[String]:
        """
        Загружает строки из .ats файла
        Поддерживает только новый JSON формат
        """
        file_path = Path(file_path) if isinstance(file_path, str) else file_path

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                import json

                data = json.load(f)
                return [String.from_string_data(item) for item in data]
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Если файл не в JSON формате, пробуем конвертировать
            from .ats_converter import convert_ats_file

            try:
                data = convert_ats_file(file_path)
                # Сохраняем в новом формате
                ATSParser.save_ats(file_path, data)
                return data
            except Exception as e:
                print(f"Ошибка при загрузке файла {file_path}: {e}")
                return []

    @staticmethod
    def save_ats(file_path: str | Path, strings: list[String]):
        """
        Сохраняет строки в .ats файл
        """
        file_path = Path(file_path) if isinstance(file_path, str) else file_path
        with open(file_path, "w", encoding="utf-8") as f:
            import json

            data = [string.to_string_data() for string in strings]
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_from_folder(self, folder_path: str | Path) -> dict[str, list[String]]:
        """
        Загружает все .ats файлы из папки и сохраняет в базу данных
        Возвращает словарь {имя_плагина: список_строк}
        """
        folder_path = Path(folder_path) if isinstance(folder_path, str) else folder_path
        translations = {}

        with self.db:
            for ats_file in folder_path.glob("*.ats"):
                plugin_name = ats_file.stem

                # Если переводы уже есть в базе, загружаем их оттуда
                if self.db.translation_exists(plugin_name):
                    translations[plugin_name] = [
                        String.from_string_data(data)
                        for data in self.db.get_translations(plugin_name)
                    ]
                else:
                    # Если нет - парсим файл и сохраняем в базу
                    strings = self.load_ats(ats_file)
                    self.db.save_translations(plugin_name, strings)
                    translations[plugin_name] = strings

        return translations

    def save_to_folder(
        self, folder_path: str | Path, translations: dict[str, list[String]]
    ):
        """
        Сохраняет все переводы в папку как .ats файлы и в базу данных
        """
        folder_path.mkdir(parents=True, exist_ok=True)

        with self.db:
            for plugin_name, strings in translations.items():
                # Сохраняем в файл
                file_path = folder_path / f"{plugin_name}.ats"
                self.save_ats(file_path, strings)

                # Сохраняем в базу данных
                self.db.save_translations(plugin_name, strings)

    def clear_database(self):
        """
        Очищает базу данных переводов
        """
        with self.db:
            self.db.conn.execute("DELETE FROM translations")

    def search_translations(
        self,
        search_query: str,
        search_in_original: bool = True,
        search_in_translated: bool = True,
        case_insensitive: bool = True,
        translations_folder: str = "skyrim_strings/russian",
    ) -> list[dict]:
        """
        Ищет переводы по запросу в базе данных. Если база пуста, парсит файлы, сохраняет в базу и возвращает результат из базы.

        Args:
            search_query: Строка для поиска
            search_in_original: Искать в оригинальных строках (английский)
            search_in_translated: Искать в переведенных строках (русский)
            case_insensitive: Поиск без учета регистра
            translations_folder: Папка с переводами
        """
        try:
            # Убедимся, что соединение с базой данных установлено
            if not hasattr(self.db, "conn") or self.db.conn is None:
                self.db.connect()
                print("Соединение с базой данных установлено")

            # Проверяем, есть ли данные в базе
            with self.db:
                cursor = self.db.conn.execute("SELECT 1 FROM translations LIMIT 1")
                if not cursor.fetchone():
                    print("База данных пуста, начинаем загрузку переводов")
                    # Очищаем базу данных перед загрузкой новых переводов
                    self.db.clear_database()

                    # Загружаем переводы из папки
                    try:
                        # Получаем абсолютный путь к папке с переводами
                        translations_path = (
                            Path(__file__).parent.parent / translations_folder
                        )
                        print(f"Путь к переводам: {translations_path}")

                        if not translations_path.exists():
                            print(f"Папка с переводами не найдена: {translations_path}")
                            return []

                        translations = self.load_from_folder(translations_path)
                        print(f"Загружено {len(translations)} плагинов")

                        # Сохраняем все переводы в базу
                        for plugin_name, strings in translations.items():
                            self.db.save_translations(plugin_name, strings)
                        print("Переводы успешно загружены в базу данных")
                    except Exception as e:
                        print(f"Ошибка при загрузке переводов: {e}")
                        return []
        except Exception as e:
            print(f"Ошибка при работе с базой данных: {e}")
            return []

        # Получаем все данные из базы
        with self.db:
            cursor = self.db.conn.execute(
                """
                SELECT plugin_name, editor_id, form_id, string_index, type, 
                       original_string, translated_string, status
                FROM translations
            """
            )
            all_data = [
                {
                    "plugin_name": row[0],
                    "editor_id": row[1],
                    "form_id": row[2],
                    "index": row[3],
                    "type": row[4],
                    "original_string": row[5],
                    "translated_string": row[6],
                    "status": row[7],
                }
                for row in cursor.fetchall()
            ]

        # Подготовка поискового запроса
        if case_insensitive:
            search_query = search_query.lower()
            search_func = lambda text: search_query in text.lower()
        else:
            search_func = lambda text: search_query in text

        # Фильтруем и сортируем результаты
        results = []
        for item in all_data:
            if (search_in_original and search_func(item["original_string"])) or (
                search_in_translated
                and item["translated_string"]
                and search_func(item["translated_string"])
            ):
                # Вычисляем длину строки, содержащей искомое слово
                if search_in_original and search_func(item["original_string"]):
                    length = len(item["original_string"])
                else:
                    length = len(item["translated_string"])
                results.append((length, item))

        # Сортируем по длине строки (от меньшего к большему)
        results.sort(key=lambda x: x[0])

        # Оставляем только 10 лучших результатов
        top_results = [item for (_, item) in results[:10]]

        print(f"Найдено строк: {len(results)}, показано: {len(top_results)}")
        return top_results
