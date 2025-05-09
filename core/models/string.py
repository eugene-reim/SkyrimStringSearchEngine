from enum import Enum


class StringType(Enum):
    STRINGS = "strings"
    DLSTRINGS = "dlstrings"
    ILSTRINGS = "ilstrings"


class TranslationStatus(Enum):
    UNTRANSLATED = "untranslated"
    TRANSLATED = "translated"
    VERIFIED = "verified"
    PROBLEM = "problem"


class String:
    def __init__(
        self,
        string_index: int,
        original_string: str,
        translated_string: str = None,
        editor_id: str = None,
        form_id: str = None,
        type: StringType = StringType.STRINGS,
        status: TranslationStatus = TranslationStatus.UNTRANSLATED,
    ):
        self.string_index = string_index
        self.original_string = original_string
        self.translated_string = translated_string
        self.editor_id = editor_id
        self.form_id = form_id
        self.type = type
        self.status = status

    def __repr__(self):
        return f"String(index={self.string_index}, original='{self.original_string[:20]}...')"
