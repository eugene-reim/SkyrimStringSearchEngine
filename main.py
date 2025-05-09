from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from api.v1.endpoints import router
from initialize import initialize_application
import os

# API эндпоинт
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
app.include_router(router, prefix="/api/v1")


# Главная страница
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


if __name__ == "__main__":
    import os

    os.environ["RELOADER_RUN"] = "true" if os.environ.get("RELOADER_RUN") else "false"

    if os.environ["RELOADER_RUN"] == "false":
        initialize_application()

    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
