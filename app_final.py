import logging

from fastapi import FastAPI, HTTPException, Query

import os

from contextlib import asynccontextmanager

# Каркас: FastAPI - фреймворк, каждый маршрут объявляется декоратором @app.get(...)
APP_NAME = os.getenv("APP_NAME", "Grade Calculator")
APP_AUTHOR = os.getenv("APP_AUTHOR", "Unknown author")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
APP_SCALE_MAX = float(os.getenv("APP_SCALE_MAX", "10"))


# Логи: basicConfig выводит события в консоль запуска
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("grade_calculator")


@asynccontextmanager
async def lifespan(application: FastAPI):
    # Событие "запуск" в лог - требование из PDF. Lifespan - современная замена on_event
    logger.info("Приложение %s (версия %s) запущено. Автор: %s", APP_NAME, APP_VERSION, APP_AUTHOR)
    for course_id, course in COURSES.items():
        total = sum(course["components"].values())
        if abs(total * APP_SCALE_MAX - course["max_total"]) > 0.001:
            logger.warning(
                "У курса '%s' сумма весов даёт %.2f баллов, а заявлено %.1f — проверьте схему оценивания",
                course_id, total * APP_SCALE_MAX, course["max_total"],
            )
    yield


app = FastAPI(title=APP_NAME, lifespan=lifespan)



@app.get("/")
def root():
    # Стартовая страница-указатель
        return {"app": APP_NAME, "author": APP_AUTHOR, "docs": "/docs"}


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


def parse_scores(course: dict, raw: str) -> dict:
    # Разбираем строку 'hw1:8,hw2:9' и проверяем каждое значение
    scores = {}
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        name, sep, value = part.partition(":")
        if not sep:
            raise HTTPException(status_code=400, detail=f"Неверный формат '{part}', ожидается 'имя:оценка'")
        name = name.strip()
        if name not in course["components"]:
            raise HTTPException(status_code=400, detail=f"Компонент '{name}' не входит в курс '{course['name']}'")
        try:
            score = float(value)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Оценка '{value}' не является числом")
        if not 0 <= score <= APP_SCALE_MAX:
            raise HTTPException(status_code=400, detail=f"Оценка '{name}' должна быть от 0 до {APP_SCALE_MAX}")
        scores[name] = score
    if not scores:
        raise HTTPException(status_code=400, detail="Не передано ни одной оценки")
    return scores


@app.get("/grade/{course_id}")
def grade(course_id: str, scores: str = Query(description="Оценки в формате 'hw1:8,hw2:9'")):
    course = get_course(course_id)
    parsed = parse_scores(course, scores)
    # Взвешенная сумма только по переданным компонентам
    accumulated = sum(course["components"][name] * value for name, value in parsed.items())
    known_weight = sum(course["components"][name] for name in parsed)
    final_grade = min(accumulated, course["final_max"])
    logger.info("Курс '%s': накоплено %.2f, итог %.2f", course_id, accumulated, final_grade)
    return {
        "course": course["name"],
        "scores": parsed,
        "accumulated": round(accumulated, 2),
        "known_weight": round(known_weight, 2),
        "remaining_weight": round(course["max_total"] / APP_SCALE_MAX - known_weight, 2),
        "final_grade": round(final_grade, 2),
        "capped": accumulated > course["final_max"],
    }


@app.get("/target/{course_id}")
def target(
    course_id: str,
    known: str = Query(description="Уже известные оценки в формате 'hw1:8,hw2:9'"),
    target_grade: float = Query(description="Желаемая итоговая оценка"),
):
    course = get_course(course_id)
    if not 0 <= target_grade <= course["final_max"]:
        raise HTTPException(
            status_code=400,
            detail=f"Целевая оценка должна быть от 0 до {course['final_max']} для курса '{course['name']}'",
        )
    parsed = parse_scores(course, known)
    accumulated = sum(course["components"][name] * value for name, value in parsed.items())
    total_weight = course["max_total"] / APP_SCALE_MAX
    remaining = round(total_weight - sum(course["components"][name] for name in parsed), 2)

    if remaining <= 0:
        feasible = accumulated >= target_grade
        return {
            "course": course["name"],
            "accumulated": round(accumulated, 2),
            "remaining_weight": 0.0,
            "feasible": feasible,
            "required_score": None,
            "message": (
                "Все компоненты сданы, итог определён окончательно"
                if feasible
                else f"Желаемый итог {target_grade} уже недостижим: накоплено {round(accumulated, 2)}"
            ),
        }

    # x = (цель - накоплено) / вес оставшихся компонентов
    required = (target_grade - accumulated) / remaining
    feasible = 0 <= required <= APP_SCALE_MAX
    result = {
        "course": course["name"],
        "accumulated": round(accumulated, 2),
        "remaining_weight": remaining,
        "target_grade": target_grade,
        "feasible": feasible,
        "required_score": round(required, 2) if feasible else None,
    }
    if feasible:
        result["message"] = f"Для итога {target_grade} нужно набрать {round(required, 2)} за оставшиеся компоненты"
    else:
        top = round(min(accumulated + remaining * APP_SCALE_MAX, course["final_max"]), 2)
        result["message"] = f"Цель {target_grade} недостижима: максимум при текущих накоплениях — {top}"
    logger.info("Курс '%s': цель %.1f, достижима: %s", course_id, target_grade, feasible)
    return result
