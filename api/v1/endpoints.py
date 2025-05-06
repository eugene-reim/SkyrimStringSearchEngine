from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from skyrim_translator.core.parser import ATSParser

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

parser = ATSParser()


@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/search")
async def search_translations(
    query: str,
    search_in_original: bool = True,
    search_in_translated: bool = True,
    case_insensitive: bool = True,
):
    results = parser.search_translations(
        query,
        search_in_original=search_in_original,
        search_in_translated=search_in_translated,
        case_insensitive=case_insensitive,
    )
    print(f"Найдено результатов: {len(results)}")
    if results:
        print("Пример результата:", results[0])
    return {"results": results}
