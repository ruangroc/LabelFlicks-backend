from fastapi.testclient import TestClient
from sql_app.database import SessionLocal, engine
from sql_app import models
from main import app, get_db
import uuid

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

def test_create_and_try_get_second_project():
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

    # Getting a project with an invalid UUID shouldn't work
    response = client.get(f"/projects/{project_id2}4321abc")
    assert response.status_code == 400
    data = response.json()
    assert data["message"] == "Project ID " + project_id2 + "4321abc is not a valid UUID"

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

def test_create_project_with_same_name():
    response = client.post(
        "/projects",
        json={"name": "testproject1", "frame_extraction_rate": 1},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["message"] == "Error: there is already a project named testproject1"

def test_upload_one_video():
    # Step 1: create a project
    project_id = ""
    response = client.post(
        "/projects",
        json={"name": "testproject3", "frame_extraction_rate": 1},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "testproject3"
    assert data["frame_extraction_rate"] == 1
    assert data["percent_labeled"] == 0
    assert "id" in data
    project_id = data["id"]

    # Step 2: upload a video
    test_video_name = "president-mckinley-oath.mp4"
    upload_response = client.post(
        f"/projects/{project_id}/videos",
        files={"video": open("./test_videos/" + test_video_name, "rb")}
    )
    data = upload_response.json()
    print(data)
    assert upload_response.status_code == 200
    assert data["id"] == project_id
    assert data["video_id"]
    assert uuid.UUID(data["video_id"])

    # Uploading with invalid project UUID should fail
    response = client.post(
        f"/projects/{project_id}4321abc/videos",
        files={"video": open("./test_videos/" + test_video_name, "rb")}
    )
    assert response.status_code == 400
    data = response.json()
    assert data["message"] == "Project ID " + str(project_id) + "4321abc is not a valid UUID"

def test_upload_video_to_nonexistent_project():
    # Uploading to a non-existent project should fail
    fake_project_id = uuid.UUID('12345678123456781234567812345678')
    test_video_name = "president-mckinley-oath.mp4"
    upload_response = client.post(
        f"/projects/{fake_project_id}/videos",
        files={"video": open("./test_videos/" + test_video_name, "rb")}
    )
    assert upload_response.status_code == 404
    data = upload_response.json()
    assert data["message"] == "Project with ID " + str(fake_project_id) + " not found"