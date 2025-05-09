import enum
import logging
from pathlib import Path
from typing import Dict, Tuple
from core.logger import setup_logging


class StringContainerType(enum.IntEnum):
    Strings = 0
    DLStrings = 1
    ILStrings = 2


class SkyrimStringParser:
    def __init__(self):
        setup_logging()
        self.logger = logging.getLogger(__name__)

    def _clean_string(self, s: str) -> str:
        """Удаляет нулевые символы и лишние пробелы из строк Skyrim"""
        return s.replace("\u0000", "").strip() if s else s

    def parse_strings_file(self, file_path: str) -> Dict[int, str]:
        """Parse single .strings/.dlstrings/.ilstrings file"""
        path = Path(file_path)

        try:
            ext = path.suffix.lower()
            if ext == ".strings":
                type_ = StringContainerType.Strings
            elif ext == ".dlstrings":
                type_ = StringContainerType.DLStrings
            elif ext == ".ilstrings":
                type_ = StringContainerType.ILStrings
            else:
                raise ValueError(f"Unsupported file extension: {ext}")

            with open(file_path, "rb") as f:
                count = int.from_bytes(f.read(4), byteorder="little")
                size = int.from_bytes(f.read(4), byteorder="little")

                directory = []
                for _ in range(count):
                    string_id = int.from_bytes(f.read(4), byteorder="little")
                    offset = int.from_bytes(f.read(4), byteorder="little")
                    directory.append((string_id, offset))

                strings = {}
                for string_id, offset in directory:
                    f.seek(8 + (count * 8) + offset)

                    if type_ == StringContainerType.Strings:
                        chars = []
                        while True:
                            char = f.read(1)
                            if char == b"\x00":
                                break
                            chars.append(char)
                        string_bytes = b"".join(chars)
                    else:
                        str_size = int.from_bytes(f.read(4), byteorder="little")
                        string_bytes = f.read(str_size)

                    try:
                        string_text = string_bytes.decode("utf-8")
                    except UnicodeDecodeError:
                        string_text = string_bytes.decode("cp1252")
                    strings[string_id] = self._clean_string(string_text)

                return strings

        except Exception as e:
            self.logger.error(f"Error parsing strings file: {str(e)}")
            raise

    def parse_language_pair(
        self, eng_file: str, rus_file: str
    ) -> Dict[int, Tuple[str, str]]:
        """Parse pair of english/russian files"""
        eng_strings = self.parse_strings_file(eng_file)
        rus_strings = self.parse_strings_file(rus_file)

        combined = {}
        for string_id, eng_text in eng_strings.items():
            rus_text = rus_strings.get(string_id, "")
            combined[string_id] = (
                self._clean_string(eng_text),
                self._clean_string(rus_text),
            )

        return combined

    def get_plugin_name(self, filename: str) -> str:
        """Extract plugin name from filename (e.g. 'dawnguard_english.strings' -> 'dawnguard')"""
        return filename.split("_")[0]
