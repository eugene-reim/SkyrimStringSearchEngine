import enum
import os
import logging
from pathlib import Path
from typing import Dict, List, Tuple
from core.logger import setup_logging
from db.handler import DBHandler


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
        """Extract plugin name from filename"""
        return filename.split("_")[0]


def find_language_pairs(directory: str) -> List[Tuple[str, str]]:
    """Find matching english/russian file pairs in directory"""
    files = os.listdir(directory)
    eng_files = [f for f in files if "_english." in f]
    rus_files = [f for f in files if "_russian." in f]

    pairs = []
    for eng_file in eng_files:
        parts = eng_file.split("_english.")
        if len(parts) != 2:
            continue
        base_name = parts[0]
        extension = parts[1]
        rus_file = f"{base_name}_russian.{extension}"
        if rus_file in rus_files:
            pairs.append(
                (os.path.join(directory, eng_file), os.path.join(directory, rus_file))
            )

    return pairs


def save_to_db(db_handler, plugin_name: str, strings: Dict[int, Tuple[str, str]]):
    """Save parsed strings to database"""
    logger = logging.getLogger(__name__)
    try:
        return db_handler.save_translations(plugin_name, strings)
    except Exception as e:
        logger.error(f"Failed to save translations: {e}")
        return 0


def parse_all_files(
    directory: str, db_handler: DBHandler
) -> Dict[str, Dict[int, Tuple[str, str]]]:
    """Parse all language pairs in directory and save to DB"""
    setup_logging()
    logger = logging.getLogger(__name__)
    parser = SkyrimStringParser()

    pairs = find_language_pairs(directory)
    if not pairs:
        logger.warning(f"No language pairs found in {directory}")
        return {}

    results = {}
    total_saved = 0
    total_files = 0
    total_strings = 0

    for eng_path, rus_path in pairs:
        try:
            plugin_name = parser.get_plugin_name(Path(eng_path).name)
            strings = parser.parse_language_pair(eng_path, rus_path)
            saved = save_to_db(db_handler, plugin_name, strings)
            results[plugin_name] = strings
            total_saved += saved
            total_files += 1
            total_strings += len(strings)
        except Exception as e:
            logger.error(f"Failed to process file pair: {e}")
            continue

    logger.info(f"Processed {total_files} file pairs, {total_strings} strings total")
    logger.info(f"Saved {total_saved} new strings to database")
    return results


if __name__ == "__main__":
    data_dir = "skyrim_strings"
    if not os.path.exists(data_dir):
        raise FileNotFoundError(f"Directory {data_dir} not found")

    with DBHandler() as db_handler:
        all_strings = parse_all_files(data_dir, db_handler)
        print(f"Successfully processed {len(all_strings)} mods")
