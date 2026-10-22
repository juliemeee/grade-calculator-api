import logging

from fastapi import FastAPI, HTTPException, Query

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


# Каталог курсов: веса - это данные, поэтому «формула» у каждого курса своя
# max_total - сколько максимум можно накопить, final_max - потолок итоговой оценки
COURSES = {
    "dns": {
        "name": "Дискретные и непрерывные структуры",
        "components": {
            "hw1": 0.2,
            "hw2": 0.1,
            "hw3": 0.2,
            "hw4": 0.1,
            "lecture_work": 0.1,
            "exam": 0.4,
        },
        "max_total": 11.0,
        "final_max": 10.0,
    },
    "python": {
        "name": "Программирование на Python",
        "components": {
            "hw": 0.1,
            "tests": 0.2,
            "self_work": 0.2,
            "exam": 0.5,
        },
        "max_total": 10.0,
        "final_max": 10.0,
    },
    "infra": {
        "name": "Инфраструктура и администрирование",
        "components": {
            "final_project": 1.0,
        },
        "max_total": 10.0,
        "final_max": 10.0,
    },
}


def get_course(course_id: str) -> dict:
    # Ищем курс или возвращаем ошибку
    course = COURSES.get(course_id)
    if course is None:
        raise HTTPException(status_code=404, detail=f"Курс '{course_id}' не найден")
    return course


@app.get("/courses")
def courses():
    # Список всех предметов со схемой весов
    result = []
    for course_id, course in COURSES.items():
        result.append({
            "id": course_id,
            "name": course["name"],
            "components": course["components"],
            "total_weight": round(sum(course["components"].values()), 2),
            "max_total": course["max_total"],
            "final_max": course["final_max"],
        })
    return {"courses": result}


@app.get("/courses/{course_id}")
def course_detail(course_id: str):
    # Маршрут с параметром в пути
    course = get_course(course_id)
    return {
        "id": course_id,
        "name": course["name"],
        "components": course["components"],
    }


