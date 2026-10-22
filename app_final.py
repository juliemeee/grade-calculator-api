import logging

from fastapi import FastAPI

# Каркас: FastAPI - фреймворк, каждый маршрут объявляется декоратором @app.get(...)
app = FastAPI(title="Grade Calculator")

# Логи: basicConfig выводит события в консоль запуска
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("grade_calculator")


@app.on_event("startup")
def log_startup():
    # Событие "запуск" в лог - требование из PDF
    logger.info("Приложение запущено")


@app.get("/")
def root():
    # Стартовая страница-указатель
    return {"app": "Grade Calculator", "docs": "/docs"}


@app.get("/health")
def health():
    # Проверка работоспособности
    return {"status": "ok"}


@app.get("/version")
def version():
    # Версия приложения
    return {"version": "1.0.0"}
