"""
Модуль для конвертации старых .ats файлов (pickle) в новый формат (JSON)
"""

import pickle
import sys
import types
from pathlib import Path
from skyrim_translator.core.parser import String


class TempString:
    """
    Временный класс для совместимости со старым форматом
    """

    class String:
        class Status:
            NoTranslationRequired = 1
            TranslationComplete = 2
            TranslationIncomplete = 3
            TranslationRequired = 4


def convert_ats_file(file_path: Path) -> list[String]:
    """
    Конвертирует старый .ats файл в новый формат
    """
    try:
        # Создаем временный модуль для совместимости
        plugin_parser = types.ModuleType("plugin_parser")
        sys.modules["plugin_parser"] = plugin_parser
        plugin_parser.String = TempString
        sys.modules["plugin_parser.string"] = TempString

        # Загружаем данные
        with open(file_path, "rb") as f:
            data = pickle.load(f)

        # Преобразуем в новый формат
        converted_data = []
        for item in data:
            if isinstance(item, TempString.String):
                # Преобразуем числовой статус в Enum
                status_mapping = {
                    1: String.Status.NoTranslationRequired,
                    2: String.Status.TranslationComplete,
                    3: String.Status.TranslationIncomplete,
                    4: String.Status.TranslationRequired,
                }

                converted_data.append(
                    String(
                        editor_id=item.editor_id,
                        form_id=item.form_id,
                        index=item.index,
                        type=item.type,
                        original_string=item.original_string,
                        translated_string=item.translated_string,
                        status=status_mapping.get(
                            item.status, String.Status.TranslationRequired
                        ),
                    )
                )
            else:
                converted_data.append(item)

        return converted_data
    finally:
        # Убираем временный модуль
        if "plugin_parser" in sys.modules:
            del sys.modules["plugin_parser"]
        if "plugin_parser.string" in sys.modules:
            del sys.modules["plugin_parser.string"]
