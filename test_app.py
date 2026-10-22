from fastapi.testclient import TestClient

from app_final import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version():
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json()["version"] == "1.0.0"


def test_courses_list_contains_all_subjects():
    response = client.get("/courses")
    assert response.status_code == 200
    ids = [course["id"] for course in response.json()["courses"]]
    assert {"dns", "python", "infra"} <= set(ids)


def test_grade_for_infra():
    response = client.get("/grade/infra", params={"scores": "final_project:9"})
    assert response.status_code == 200
    data = response.json()
    assert data["accumulated"] == 9.0
    assert data["final_grade"] == 9.0


def test_grade_for_dns_caps_at_ten():
    # Сумма весов ДНС даёт 11, но итог не может быть выше 10
    response = client.get(
        "/grade/dns",
        params={"scores": "hw1:10,hw2:10,hw3:10,hw4:10,lecture_work:10,exam:10"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["accumulated"] == 11.0
    assert data["final_grade"] == 10.0
    assert data["capped"] is True


def test_grade_rejects_unknown_component():
    # Случай с ошибкой: несуществующий компонент -> 400
    response = client.get("/grade/infra", params={"scores": "essay:9"})
    assert response.status_code == 400


def test_target_feasible():
    # hw:10 (вес 0.1) + tests:8 (вес 0.2) -> накоплено 2.6, осталось 0.7
    # Для итога 7 нужно: (7 - 2.6) / 0.7 = 6.29
    response = client.get("/target/python", params={"known": "hw:10,tests:8", "target_grade": 7})
    assert response.status_code == 200
    data = response.json()
    assert data["feasible"] is True
    assert abs(data["required_score"] - 6.29) < 0.01


def test_target_infeasible():
    # С нулями за ДЗ и тесты итог 10 недостижим
    response = client.get("/target/python", params={"known": "hw:0,tests:0", "target_grade": 10})
    assert response.status_code == 200
    assert response.json()["feasible"] is False
