import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime


def setup_logging():
    """Настройка системы логирования на русском языке"""

    # Создаем папку для логов если ее нет
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Удаляем старые логи (оставляем последние 10 файлов)
    log_files = sorted(log_dir.glob("translator_*.log"), key=os.path.getmtime)
    for old_log in log_files[:-10]:
        old_log.unlink()

    # Создаем новый лог-файл с текущей датой-временем
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = log_dir / f"translator_{timestamp}.log"

    # Формат сообщений
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
        datefmt="%H:%M:%S",
    )

    # Настройка обработчика файла
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"  # 5 MB
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    # Настройка обработчика консоли
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.WARNING)

    # Основная конфигурация
    logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler])


def get_logger(name):
    """Возвращает логгер с указанным именем"""
    return logging.getLogger(name)
