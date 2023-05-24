from fastapi.testclient import TestClient
from sql_app.database import SessionLocal, engine
from sql_app import models
from main import app, get_db
import uuid
import time

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
        json={"name": "testproject1"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "testproject1"
    assert data["percent_labeled"] == 0
    assert "id" in data
    project_id1 = data["id"]

    response = client.get(f"/projects/{project_id1}")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "testproject1"
    assert data["percent_labeled"] == 0
    assert data["id"] == project_id1

def test_create_and_try_get_second_project():
    project_id2 = ""

    response = client.post(
        "/projects",
        json={"name": "testproject2"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "testproject2"
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
        json={"name": "testproject1"},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["message"] == "Error: there is already a project named testproject1"

def test_upload_one_video():
    # Step 1: create a project
    project_id = ""
    response = client.post(
        "/projects",
        json={"name": "testproject3"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "testproject3"
    assert data["percent_labeled"] == 0
    assert "id" in data
    project_id = data["id"]

    # Step 2: upload a video
    test_video_name = "president-mckinley-oath.mp4"
    upload_response = client.post(
        f"/projects/{project_id}/videos",
        files={"video": open("./test_videos/" + test_video_name, "rb")}
    )
    assert upload_response.status_code == 202
    data = upload_response.json()
    assert data["id"] == project_id
    video_id = data["video_id"]
    assert video_id
    assert uuid.UUID(video_id)

    # Provide a little time for preprocessing the video
    time.sleep(40)

    # Fetching the just-uploaded video should return additional information
    video_response = client.get(f"/videos/{video_id}")
    assert video_response.status_code == 200
    data = video_response.json()
    assert data["id"] == video_id
    assert data["project_id"] == project_id
    assert data["name"] == test_video_name
    assert data["percent_labeled"] == 0.0
    assert data["number_of_frames"] == 64  
    assert data["preprocessing_status"] == "success"

    # To double check that frames were inserted, call this
    # additional endpoint as well
    video_response = client.get(f"/videos/{video_id}/frames")
    assert video_response.status_code == 200
    data = video_response.json()
    assert data["video_id"] == video_id
    assert data["frames"]
    assert len(data["frames"]) == 64
    one_frame_id = data["frames"][0]["id"]
    another_frame_id = data["frames"][10]["id"]
    print(data["frames"][10]["labels"])
    assert data["frames"][10]["labels"]
    # assert len(data["frames"][10]["labels"]) == 2

    # To check that preprocessing worked, check that labels were 
    # created and bounding boxes inserted
    labels_response = client.get(f"/projects/{project_id}/labels")
    assert labels_response.status_code == 200
    data = labels_response.json()
    assert data["project_id"] == project_id
    assert len(data["labels"]) == 4
    label_names = [label["name"] for label in data["labels"]]
    assert "person" in label_names
    assert "car" in label_names

    boxes_response = client.get(f"/frames/{one_frame_id}/inferences")
    assert boxes_response.status_code == 200
    data = boxes_response.json()
    assert data["frame_id"] == one_frame_id
    assert len(data["bounding_boxes"]) == 0  # This frame had no detected boxes

    boxes_response = client.get(f"/frames/{another_frame_id}/inferences")
    assert boxes_response.status_code == 200
    data = boxes_response.json()
    assert data["frame_id"] == another_frame_id
    assert len(data["bounding_boxes"]) == 5  # This frame detected 4 people and 1 car

    # Uploading with invalid project UUID should fail
    response = client.post(
        f"/projects/{project_id}4321abc/videos",
        files={"video": open("./test_videos/" + test_video_name, "rb")}
    )
    assert response.status_code == 400
    data = response.json()
    assert data["message"] == "Project ID " + str(project_id) + "4321abc is not a valid UUID"

    # Trying to upload the same video again to the same project should fail
    upload_response = client.post(
        f"/projects/{project_id}/videos",
        files={"video": open("./test_videos/" + test_video_name, "rb")}
    )
    assert upload_response.status_code == 400
    data = upload_response.json()
    assert data["message"] == "Video " + test_video_name + " has already been uploaded to project with ID " + project_id

    # Fetching all video IDs related to this project should return just this one video ID
    fetch_response = client.get(f"/projects/{project_id}/videos")
    assert fetch_response.status_code == 200
    data = fetch_response.json()
    assert data["project_id"] == project_id
    assert len(data["videos"]) == 1
    assert data["videos"][0]["id"] == video_id


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

def test_upload_non_video_file():
    # Fetch an existing project and get its project UUID
    response = client.get("/projects")
    assert response.status_code == 200
    data = response.json()
    project_id = data[0]["id"]

    # Try to upload it
    upload_response = client.post(
        f"/projects/{project_id}/videos",
        files={"video": open("./test_videos/test-screenshot.png", "rb")}
    )
    assert upload_response.status_code == 400
    data = upload_response.json()
    assert data["message"] == "Video test-screenshot.png is not of content-type video/mp4"

def test_bad_fetch_all_videos_for_a_project():
    # Fetching all video IDs related to a non-UUID project ID should return an error
    bad_response = client.get("/projects/4321abc/videos")
    assert bad_response.status_code == 400
    data = bad_response.json()
    assert data["message"] == "Project ID 4321abc is not a valid UUID"

    # Fetching with a UUID that doesn't exist in the database should return an error
    new_uuid = uuid.uuid4()
    bad_response = client.get(f"/projects/{new_uuid}/videos")
    assert bad_response.status_code == 404
    data = bad_response.json()
    assert data["message"] == "Project with ID " + str(new_uuid) + " not found"

def test_bad_fetch_one_video():
    # Fetching a video with a non-UUID video ID should return an error
    bad_response = client.get("/videos/4321abc")
    assert bad_response.status_code == 400
    data = bad_response.json()
    assert data["message"] == "Video ID 4321abc is not a valid UUID"

    # Fetching with a UUID that doesn't exist in the database should return an error
    new_uuid = uuid.uuid4()
    bad_response = client.get(f"/videos/{new_uuid}")
    assert bad_response.status_code == 404
    data = bad_response.json()
    assert data["message"] == "Video with ID " + str(new_uuid) + " not found"

