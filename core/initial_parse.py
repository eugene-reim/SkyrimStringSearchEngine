import os
from pathlib import Path
from typing import Dict, List, Tuple
from core.new_parser import SkyrimStringParser
from core.logger import setup_logging
from db.handler import DBHandler
import logging


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
    """Save parsed strings to database using DBHandler's save_translations"""
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
    data_dir = "skyrim_strings/original"
    if not os.path.exists(data_dir):
        raise FileNotFoundError(f"Directory {data_dir} not found")

    with DBHandler() as db_handler:
        all_strings = parse_all_files(data_dir, db_handler)
        print(f"Successfully processed {len(all_strings)} mods")
