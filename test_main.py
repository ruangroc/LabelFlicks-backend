from fastapi.testclient import TestClient
from sql_app.database import SessionLocal, engine
from sql_app import models
from main import app, get_db

# Clear test database before creating new tables
models.Base.metadata.drop_all(bind=engine)
models.Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def override_get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_create_and_get_first_project():
    project_id1 = ""

    response = client.post(
        "/projects",
        json={"name": "testproject1", "frame_extraction_rate": 1},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "testproject1"
    assert data["frame_extraction_rate"] == 1
    assert data["percent_labeled"] == 0
    assert "id" in data
    project_id1 = data["id"]

    response = client.get(f"/projects/{project_id1}")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "testproject1"
    assert data["frame_extraction_rate"] == 1
    assert data["percent_labeled"] == 0
    assert data["id"] == project_id1

def test_create_and_get_second_project():
    project_id2 = ""

    response = client.post(
        "/projects",
        json={"name": "testproject2", "frame_extraction_rate": 2},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "testproject2"
    assert data["frame_extraction_rate"] == 2
    assert data["percent_labeled"] == 0
    assert "id" in data
    project_id2 = data["id"]

    response = client.get(f"/projects/{project_id2}")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "testproject2"
    assert data["frame_extraction_rate"] == 2
    assert data["percent_labeled"] == 0
    assert data["id"] == project_id2

def test_get_all_projects():
    response = client.get("/projects")
    assert response.status_code == 200
    assert response.json(), response.text
    data = response.json()
    assert len(data) == 2