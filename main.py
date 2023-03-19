from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uuid
from typing import Any, List, Union

# Data classes for post request bodies
from sql_app import schemas, models, crud
from sql_app.database import SessionLocal, engine
from sqlalchemy.orm import Session

# Azure related imports
import os
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Create FastAPI instance
app = FastAPI()

# Fetch database instance
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Connect to Azure storage account
load_dotenv()
connect_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
blob_service_client = None
if connect_str:
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)

# Check if testing or not
test_status = os.getenv("TEST_ENVIRONMENT")

# Specify allowed origins for requests
origins = [
    "http://localhost",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


###############################################################
# Projects endpoints
###############################################################

@app.get("/projects", response_model=List[schemas.ExistingProject])
def get_all_projects(db: Session = Depends(get_db)):
    projects = crud.get_projects(db)
    returned_projects = []

    # Convert each project from database query response model to response model
        # and also get most up to date calculations for video count and percent
        # of frames reviewed
    for project in projects:
        new_project = schemas.ExistingProject.parse_obj({
            "id": project.id,
            "name": project.name,
            "frame_extraction_rate": project.frame_extraction_rate,
            "percent_labeled": crud.get_percent_frames_reviewed(db, project.id),
            "video_count": crud.get_video_count(db, project.id)
        })
        returned_projects.append(new_project)
    
    return returned_projects


@app.post("/projects", response_model=schemas.ExistingProject)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db)):
    # TODO: validate frame_extraction rate is in expected range,
    # and later the UI can also help enforce that,
    # else default to 1 frame per second extraction rate

    if crud.get_project_by_name(db, project.name):
        return JSONResponse(status_code=400, content={"message": "Error: there is already a project named " + project.name})

    try:
        res = crud.create_project(db, project)
    except Exception as e:
        return JSONResponse(status_code=400, content={"message": "Unable to create project named " + project.name + " error: " + str(e)})

    container_name = str(res.id)
    
    if test_status != "TRUE":
        # If connected to Azure, create a container in the blob storage account
        # Otherwise, create a directory in the local file system
        if blob_service_client:
            blob_service_client.create_container(container_name)
        else:
            if not os.path.exists(container_name):
                os.makedirs(container_name)
    
    # Convert from database query response model to response model
    new_project = schemas.ExistingProject.parse_obj({
        "id": res.id,
        "name": res.name,
        "frame_extraction_rate": res.frame_extraction_rate,
        "percent_labeled": 0.0,
        "video_count": 0
    })

    return new_project


@app.get("/projects/{project_id}", response_model=schemas.ExistingProject)
def get_project(project_id: str, db: Session = Depends(get_db)):
    # Validate that project_id is a valid UUID
    try:
        uuid.UUID(project_id)
    except:
        return JSONResponse(status_code=400, content={"message": "Project ID " + project_id + " is not a valid UUID"})
    
    res = crud.get_project_by_id(db, project_id)

    if res == None:
        return JSONResponse(status_code=404, content={"message": "Project with ID " + project_id + " not found"})
    
    # Convert from database query response model to response model
    project = schemas.ExistingProject.parse_obj({
        "id": res.id,
        "name": res.name,
        "frame_extraction_rate": res.frame_extraction_rate,
        "percent_labeled": crud.get_percent_frames_reviewed(db, res.id),
        "video_count": crud.get_video_count(db, res.id)
    })

    return project


@app.put("/projects/{project_id}")
async def rename_project(project_id: str, project: schemas.ProjectCreate):
    # TODO: use project_id to update name of the project,
    # or return error for invalid id
    
    return {
        "project": {
            "id": project_id,
            "name": project["name"],
            "frame_extraction_rate": 1,
            "percent_labeled": 10
        }
    }

@app.delete("/projects/{project_id}")
def delete_project(project_id: str):
    # TODO: delete requested project and all associated
    # artifacts (videos, images, numpy files, bounding boxes)

    # TODO: return status code from SQL delete operation
    return 200


@app.get("/projects/{project_id}/labels")
def get_project_labels(project_id: str):
    # TODO: return list of labels (class names) that are used
    # for labeling boxes in this project

    return {
        "id": project_id,
        "labels": []
    }


@app.get("/projects/{project_id}/labeled-images")
def get_project_labeled_images(project_id: str):
    # TODO: use project_id to retrieve all annotated images 
    # contains (bounding boxes and class labels) for all 
    # frames from this project

    return {
        "id": project_id,
        "labeled-images": []
    }


@app.get("/projects/{project_id}/videos")
def get_project_videos(project_id: str):
    # TODO: use project_id to retrieve list of video_ids
    # associated with this project

    return {
        "id": project_id,
        "video_ids": []
    }

@app.post("/projects/{project_id}/videos")
def upload_project_video(project_id: str, video: schemas.VideoCreate):
    # TODO: upload a video related to this project

    return {
        "id": project_id,
        "video_ids": []
    }


###############################################################
# Videos endpoints
###############################################################

@app.get("/videos/{video_id}")
def get_video(video_id: str):
    # TODO: use video_id to fetch video information from database
    # TODO: calculate number_of_frames and percent_labeled by
    # querying the frames table

    return {
        "video": {
            "id": video_id,
            "name": "video-name",
            "video_url": "video-url",
            "frame_features_url": "frame-features-url",
            "frame_similarity_url": "frame-similarity-url",
            "date_uploaded": "datetime-value",
            "size_in_bytes": 1383234,
            "number_of_frames": 2500,
            "percent_labeled": 10 
        }
    }


@app.delete("/videos/{video_id}")
def delete_video(video_id: str):
    # TODO: delete requested video and all associated
    # artifacts (bounding boxes, images, numpy files)

    # TODO: return status code from SQL delete operation
    return 200


@app.get("/videos/{video_id}/frames")
def get_video_frames(video_id: str):
    # TODO: use video_id to fetch frames belonging to 
    # this video from the database

    # TODO: if there are no frames yet, then extract
    # them using the frame_extraction_rate specified
    # for the project

    return {
        "frames": [
            {
                "id": "uuid-f1",
                "project_id": "uuid-p1",
                "video_id": "uuid-v1",
                "url": "frame-url-1",
                "human_reviewed": False
            },
            {
                "id": "uuid-f2",
                "project_id": "uuid-p1",
                "video_id": "uuid-v1",
                "url": "frame-url-2",
                "human_reviewed": True
            }
        ]
    }


# count = query parameter for specifying how many frames to get
@app.get("/videos/{video_id}/random-frames")
def get_random_frames(video_id: str, count: int = 10):
    # TODO: use video_id to fetch a random set of frames not yet 
    # human-reviewed belonging to this video from the database
    
    # TODO: use query parameter to specify how many to grab
    # default can be 10 frames

    return {
        "frames": [
            {
                "id": "uuid-f1",
                "project_id": "uuid-p1",
                "video_id": "uuid-v1",
                "url": "frame-url-1",
                "human_reviewed": False
            },
            {
                "id": "uuid-f2",
                "project_id": "uuid-p1",
                "video_id": "uuid-v1",
                "url": "frame-url-2",
                "human_reviewed": False
            }
        ]
    }

# TODO: should be called by get_video_frames
# TODO: should call calculate_frame_similarity and 
# get_frame_inferences
def extract_image_features(video_id: str):
    # TODO: use video_id to fetch numpy file containing
    # image features of all frames in this video

    # TODO: if features file has not yet been created, 
    # create one, upload to cloud storage, and insert URL 
    # into Videos table in the database

    return {
        "features": {
            "video_id": video_id,
            "frame_features_url": "frame-features-url"
        }
    }


# TODO: should be called by extract_image_features
def calculate_frame_similarity(video_id: str):
    # TODO: use video_id to fetch numpy file containing
    # UMAP similarity embedding of all frames in this video

    # TODO: if similarity file has not yet been created, 
    # create one, upload to cloud storage, and insert URL 
    # into Videos table in the database

    return {
        "similarity": {
            "video_id": video_id,
            "frame_similarity_url": "frame-similarity-url"
        }
    }


###############################################################
# Frames endpoints
###############################################################

@app.get("/frames/{frame_id}")
def get_frame(frame_id: str):
    # TODO: use frame_id to fetch the requested frame from 
    # the database

    return {
        "frame": {
                "id": "uuid-f1",
                "project_id": "uuid-p1",
                "video_id": "uuid-v1",
                "url": "frame-url-1",
                "human_reviewed": False
            }
    }


@app.get("/frames/{frame_id}/most-similar-frames")
def get_most_similar_frames(frame_id: str, count: int = 10):
    # TODO: use the similarity numpy file to fetch a set of frames
    # that are most similar to the specified one and have not yet
    # been human-reviewed
    # I think will need to get the frame_similarity_url from the
    # video that this frame belongs to

    return {
        "frames": [
            {
                "id": "uuid-f1",
                "project_id": "uuid-p1",
                "video_id": "uuid-v1",
                "url": "frame-url-1",
                "human_reviewed": False
            },
            {
                "id": "uuid-f2",
                "project_id": "uuid-p1",
                "video_id": "uuid-v1",
                "url": "frame-url-2",
                "human_reviewed": False
            }
        ]
    }


@app.get("/frames/{frame_id}/least-similar-frames")
def get_least_similar_frames(frame_id: str, count: int = 10):
    # TODO: use the similarity numpy file to fetch a set of frames
    # that are least similar to the specified one and have not yet
    # been human-reviewed
    # I think will need to get the frame_similarity_url from the
    # video that this frame belongs to

    return {
        "frames": [
            {
                "id": "uuid-f1",
                "project_id": "uuid-p1",
                "video_id": "uuid-v1",
                "url": "frame-url-1",
                "human_reviewed": False
            },
            {
                "id": "uuid-f2",
                "project_id": "uuid-p1",
                "video_id": "uuid-v1",
                "url": "frame-url-2",
                "human_reviewed": False
            }
        ]
    }


@app.get("/frames/{frame_id}/inferences")
def get_frame_inferences(frame_id: str):
    # TODO: run object detection inference on this frame, 
    # insert any new bounding box or label information into
    # the database as appropriate, return bounding box and 
    # label information for this frame (if any)

    return {
        "inferences": [
            {
                "id": "uuid-b1",
                "frame_id": "uuid-f1",
                "label": "label-name",
                "url": "frame-url-1",
                "human_reviewed": False
            },
            {
                "id": "uuid-f2",
                "project_id": "uuid-p1",
                "video_id": "uuid-v1",
                "url": "frame-url-2",
                "human_reviewed": False
            }
        ]
    }


# format = query parameter for bounding box data format
@app.get("/frames/{frame_id}/annotations")
def get_frame_annotations(frame_id: str, format: str = "coco"):
    # TODO: use project_id to retrieve all bounding box and 
    # class label information for this frame
    # (no new object detection inference should be made)

    # TODO: allow user to select what format they want to export
    # the bounding boxes: COCO by default, but other options include
    # yolo, pascal_voc, and albumentations

    return {
        "format": "coco",
        "annotations": [
            {
                "bounding_box_id": "uuid-b1",
                "frame_id": "uuid-f1",
                "label": "label-name",
                "x_min": 20,
                "y_min": 40,
                "width": 100,
                "height": 200
            }
        ]
    }
