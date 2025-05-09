from fastapi import APIRouter
from db.handler import DBHandler
import logging

router = APIRouter()
db_handler = DBHandler()
logger = logging.getLogger(__name__)


# Основной эндпоинт апи для поиска
@router.get("/search")
async def search_translations(
    query: str,
    search_in_original: bool = True,
    search_in_translated: bool = True,
    case_insensitive: bool = True,
    offset: int = 0,
    limit: int = 20,
):
    try:
        logger.info(f"Поиск перевода для запроса: {query}")

        logger.debug(f"Параметры поиска: query={query}, offset={offset}, limit={limit}")
        try:
            results, matches, total = db_handler.search_translations(
                query,
                search_in_original=search_in_original,
                search_in_translated=search_in_translated,
                case_insensitive=case_insensitive,
                offset=offset,
                limit=limit,
            )
            logger.debug(f"Получено результатов: {len(results)}")
        except Exception as e:
            logger.error(f"Ошибка в search_translations: {e}", exc_info=True)
            raise

        response = {
            "results": results if results else [],
            "stats": {"matches": matches, "total": total},
        }
        logger.info(f"Найдено результатов: {len(results) if results else 0}")

        if results:
            logger.debug(f"Пример результата: {results[0]}")

        return response
    except Exception as e:
        logger.error(f"Ошибка при поиске: {e}", exc_info=True)
        return {"results": [], "error": str(e)}
