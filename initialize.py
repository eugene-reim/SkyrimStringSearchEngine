import os
import sqlite3
from pathlib import Path
from core.initial_parse import parse_all_files
from core.logger import setup_logging
from db.handler import DBHandler
from db.handler import DBHandler
import logging


def initialize_application():
    """Initialize all application components"""
    if os.environ.get("RELOADER_RUN") == "true":
        return

    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)

    # Initialize database
    db_handler = DBHandler()

    try:
        # Check if we need to parse files
        db_path = os.path.abspath("database/translations.db")
        need_parse = False

        logger.info(f"Checking database at: {db_path}")

        if not os.path.exists(db_path):
            need_parse = True
            logger.info("Database file not found, starting initial parsing...")
        else:
            # Verify database file is valid
            db_size = os.path.getsize(db_path)
            if db_size == 0:
                need_parse = True
                logger.warning(
                    f"Database file is empty (0 bytes), starting initial parsing..."
                )
                os.remove(db_path)  # Remove invalid empty file
            else:
                # Verify database integrity using DBHandler
                try:
                    with DBHandler() as db:
                        # Check if translations table exists
                        table_exists = db.conn.execute(
                            "SELECT name FROM sqlite_master WHERE type='table' AND name='translations'"
                        ).fetchone()

                        if not table_exists:
                            need_parse = True
                            logger.warning(
                                "Translations table not found, starting initial parsing..."
                            )
                        else:
                            # Get exact record count with additional diagnostics
                            count = db.conn.execute(
                                "SELECT COUNT(*) FROM translations"
                            ).fetchone()[0]

                            if count == 0:
                                need_parse = True
                                logger.warning(
                                    f"Database is empty (0 records, size: {db_size} bytes), starting initial parsing..."
                                )
                            else:
                                logger.info(
                                    f"Valid database found with {count} records (size: {db_size} bytes), skipping parsing"
                                )
                                # Verify we can actually read data
                                test_record = db.conn.execute(
                                    "SELECT * FROM translations LIMIT 1"
                                ).fetchone()
                                if not test_record:
                                    need_parse = True
                                    logger.warning(
                                        "Database appears corrupted - no records can be read, starting initial parsing..."
                                    )
                except Exception as e:
                    need_parse = True
                    logger.error(
                        f"Database verification failed: {str(e)}", exc_info=True
                    )

        if need_parse:
            # Check localization files
            data_dir = "skyrim_strings/original"
            if not os.path.exists(data_dir):
                logger.error(f"Localization directory not found: {data_dir}")
                raise FileNotFoundError(f"Directory {data_dir} not found")

            # Парсинг и проверка результата
            parse_all_files(data_dir, db_handler)

            # Проверяем что данные сохранились
            with DBHandler() as db:
                # Проверяем физическое сохранение файла БД
                db_size = os.path.getsize("database/translations.db")
                logger.info(f"Database file size after parsing: {db_size} bytes")

                # Проверяем записи в БД
                count = db.conn.execute("SELECT COUNT(*) FROM translations").fetchone()[
                    0
                ]
                if count == 0:
                    logger.error("No records were saved to database after parsing!")
                    # Дополнительная диагностика
                    tables = db.conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                    logger.error(f"Existing tables: {tables}")
                    raise RuntimeError("Failed to save parsed data to database")
                else:
                    logger.info(
                        f"Initial parsing completed. Saved {count} records to database"
                    )
                    # Проверяем целостность БД
                    integrity = db.conn.execute("PRAGMA integrity_check").fetchone()[0]
                    logger.info(f"Database integrity check: {integrity}")
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        raise
    finally:
        pass


if __name__ == "__main__":
    initialize_application()
