from fastapi import Depends, FastAPI, BackgroundTasks, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uuid
from typing import List

# Data classes for post request bodies
from sql_app import schemas, models, crud
from sql_app.database import SessionLocal, engine
from sqlalchemy.orm import Session

# Azure related imports
import os
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

# Computer vision related imports
import numpy as np
import cv2
from io import BytesIO
import tempfile
from ultralytics import YOLO
import torchvision.transforms.functional as TF
from efficientnet_pytorch import EfficientNet
from model_training import ClassifierManager
import pickle

# Load pre-trained YOLO object detection model
yolo_model = YOLO("yolov8n.pt")

# Load pre-trained image feature extraction model (EfficientNet)
feature_extraction_model = EfficientNet.from_pretrained("efficientnet-b0")
feature_extraction_model.eval()

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
# Utility functions
###############################################################


# Useful for calculating percent of frames reviewed per project
# or per video in a project
def calculate_percent_frames_reviewed(object):
    # If no frames exist for this video, no need to calculate percent reviewed
    total = len(object.frames)
    if total == 0:
        return 0.0

    reviewed = 0
    for i in range(total):
        if object.frames[i].human_reviewed:
            reviewed += 1
    return round(100 * (reviewed / total), 2)


def predict_bounding_boxes(
    frame_image, frame_id: uuid.UUID, project_id: uuid.UUID, db: Session
):
    # Apply pretrained object detection model to each frame to generate bounding boxes
    yolo_results = yolo_model(frame_image)
    yolo_class_ids_to_names = yolo_results[0].names

    # Insert any new detected labels into the database
    labels_to_insert = []
    label_names = np.unique(
        [yolo_class_ids_to_names[int(box.cls)] for box in yolo_results[0].boxes]
    )
    for label_name in label_names:
        if crud.get_label_by_name_and_project(db, label_name, project_id) == None:
            labels_to_insert.append(
                schemas.LabelCreate.parse_obj(
                    {"project_id": project_id, "name": str(label_name)}
                )
            )

    if len(labels_to_insert) > 0:
        crud.insert_labels(db, labels_to_insert)

    # Update mapping for the IDs from the database's Label table
    label_names_to_db_ids = {}
    all_project_labels = crud.get_labels_by_project(db, project_id)
    for label in all_project_labels:
        label_names_to_db_ids[label.name] = label.id

    # Create mapping from label name to label ids

    # Put info about each box into a standard format
    boxes = []
    for box in yolo_results[0].boxes:
        # Box information given as tensor([[float, float, float, float]])
        x_top_left = int(box.xyxy[0][0])
        y_top_left = int(box.xyxy[0][1])
        x_bottom_right = int(box.xyxy[0][2])
        y_bottom_right = int(box.xyxy[0][3])
        width = int(box.xywh[0][2])
        height = int(box.xywh[0][3])
        label_name = yolo_class_ids_to_names[int(box.cls)]

        # Crop image to what's inside the bounding box and get the feature vector for that cropped area
        cropped_image = TF.crop(
            TF.to_tensor(frame_image), y_top_left, x_top_left, height, width
        ).unsqueeze(0)
        padded_image = TF.resize(cropped_image, (64, 64), antialias=True)
        image_features = feature_extraction_model.extract_features(padded_image)
        image_features = pickle.dumps(image_features.detach())

        db_box = schemas.BoundingBoxCreate.parse_obj(
            {
                "x_top_left": x_top_left,
                "y_top_left": y_top_left,
                "x_bottom_right": x_bottom_right,
                "y_bottom_right": y_bottom_right,
                "width": width,
                "height": height,
                "frame_id": frame_id,
                "label_id": label_names_to_db_ids[label_name],
                "image_features": image_features,
                "prediction": True,
            }
        )
        boxes.append(db_box)

    # Insert all bounding boxes for this frame into the database
    crud.insert_boxes(db, boxes)
    return


# Preprocessing a video involves extracting frames (1 fps)
# and using a pretrained object detection model to generate
# initial bounding boxes and labels. This will be run in
# a FastAPI background task.
def preprocess_video(
    video_bytes,
    storage_location,
    video_id: uuid.UUID,
    project_id: uuid.UUID,
    db: Session,
):
    # Signify that preprocessing has begun
    crud.set_video_preprocessing_status(db, video_id, "in_progress")

    # Video is sent as bytes but OpenCV's VideoCapture only reads
    # videos from files, so using a temp file here
    with tempfile.NamedTemporaryFile() as temp:
        temp.write(video_bytes)
        vidcap = cv2.VideoCapture(temp.name)

    # Figure out number of frames and frames per second rate
    num_frames = vidcap.get(cv2.CAP_PROP_FRAME_COUNT)
    fps = vidcap.get(cv2.CAP_PROP_FPS)

    # Figure out frame width and height (returned as floats but we'll round)
    width = round(vidcap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = round(vidcap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    index = 0
    for frame in np.arange(0, num_frames, fps):
        vidcap.set(cv2.CAP_PROP_POS_FRAMES, frame)
        hasFrames, image = vidcap.read()

        if not hasFrames:
            # If frames could not be extracted, signify that
            # preprocessing failed for this video so caller can restart
            crud.set_video_preprocessing_status(db, video_id, "failed")
            return

        # Otherwise continue and save frame as image in desired storage path
        # and note whether frame insertion was successful
        inserted_frame = False
        if storage_location["azure"]:
            # First connect to storage container using the desired destination path
            blob_client = blob_service_client.get_blob_client(
                container=storage_location["container"],
                blob=storage_location["path"] + "/" + str(index) + ".jpg",
            )

            # Convert from OpenCV's output array into image bytes before uploading
            is_success, buffer = cv2.imencode(".jpg", image)

            if not is_success:
                # Signify that preprocessing failed for this video so caller can restart
                crud.set_video_preprocessing_status(db, video_id, "failed")
                return

            image_bytes = BytesIO(buffer)
            blob_client.upload_blob(image_bytes)

            new_frame = schemas.FrameCreate.parse_obj(
                {
                    "width": width,
                    "height": height,
                    "project_id": project_id,
                    "video_id": video_id,
                    "frame_url": storage_location["path"] + "/" + str(index) + ".jpg",
                }
            )
            inserted_frame = crud.insert_one_frame(db, new_frame)
            # if inserted_frame:
            #     predict_bounding_boxes(image, inserted_frame.id, project_id, db)

        else:
            is_success = cv2.imwrite(
                storage_location["path"] + "/" + str(index) + ".jpg", image
            )

            if not is_success:
                # Signify that preprocessing failed for this video so caller can restart
                crud.set_video_preprocessing_status(db, video_id, "failed")
                return

            new_frame = schemas.FrameCreate.parse_obj(
                {
                    "width": width,
                    "height": height,
                    "project_id": project_id,
                    "video_id": video_id,
                    "frame_url": storage_location["path"] + "/" + str(index) + ".jpg",
                }
            )
            inserted_frame = crud.insert_one_frame(db, new_frame)
            # if inserted_frame:
            #     predict_bounding_boxes(image, inserted_frame.id, project_id, db)

        if inserted_frame:
            predict_bounding_boxes(image, inserted_frame.id, project_id, db)

        index += 1

    # Update done_processing field for this video
    crud.set_video_preprocessing_status(db, video_id, "success")


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
        new_project = schemas.ExistingProject.parse_obj(
            {
                "id": project.id,
                "name": project.name,
                "percent_labeled": calculate_percent_frames_reviewed(project),
                "video_count": len(project.videos),
            }
        )
        returned_projects.append(new_project)

    return returned_projects


@app.post("/projects", response_model=schemas.ExistingProject)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db)):
    if crud.get_project_by_name(db, project.name):
        return JSONResponse(
            status_code=400,
            content={
                "message": "Error: there is already a project named " + project.name
            },
        )

    try:
        res = crud.create_project(db, project)
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={
                "message": "Unable to create project named "
                + project.name
                + " error: "
                + str(e)
            },
        )

    container_name = str(res.name)

    # If connected to Azure, create a container in the blob storage account
    # Otherwise, create a directory in the local file system
    if blob_service_client:
        blob_service_client.create_container(container_name)
    else:
        if not os.path.exists("./local_projects/" + container_name):
            os.makedirs("./local_projects/" + container_name)

    # Convert from database query response model to response model
    new_project = schemas.ExistingProject.parse_obj(
        {"id": res.id, "name": res.name, "percent_labeled": 0.0, "video_count": 0}
    )

    return new_project


@app.get("/projects/{project_id}", response_model=schemas.ExistingProject)
def get_project(project_id: str, db: Session = Depends(get_db)):
    # Validate that project_id is a valid UUID
    try:
        uuid.UUID(project_id)
    except:
        return JSONResponse(
            status_code=400,
            content={"message": "Project ID " + project_id + " is not a valid UUID"},
        )

    res = crud.get_project_by_id(db, project_id)

    if res == None:
        return JSONResponse(
            status_code=404,
            content={"message": "Project with ID " + project_id + " not found"},
        )

    # Convert from database query response model to response model
    project = schemas.ExistingProject.parse_obj(
        {
            "id": res.id,
            "name": res.name,
            "percent_labeled": calculate_percent_frames_reviewed(res),
            "video_count": len(res.videos),
        }
    )

    return project


@app.put("/projects/{project_id}")
async def rename_project(project_id: str, project: schemas.ProjectCreate):
    # TODO: use project_id to update name of the project,
    # or return error for invalid id

    return {
        "project": {"id": project_id, "name": project["name"], "percent_labeled": 10}
    }


@app.delete("/projects/{project_id}")
def delete_project(project_id: str):
    # TODO: delete requested project and all associated
    # artifacts (videos, images, numpy files, bounding boxes)

    # TODO: return status code from SQL delete operation
    return 200


@app.get("/projects/{project_id}/labels")
def get_project_labels(project_id: str, db: Session = Depends(get_db)):
    # Validate that project_id is a valid UUID
    try:
        uuid.UUID(project_id)
    except:
        return JSONResponse(
            status_code=400,
            content={"message": "Project ID " + project_id + " is not a valid UUID"},
        )

    res = crud.get_project_by_id(db, project_id)

    if res == None:
        return JSONResponse(
            status_code=404,
            content={"message": "Project with ID " + project_id + " not found"},
        )

    rows_returned = crud.get_labels_by_project(db, project_id)
    labels = []
    for row in rows_returned:
        labels.append(
            schemas.Label.parse_obj(
                {"id": row.id, "name": row.name, "project_id": row.project_id}
            )
        )

    return {"project_id": project_id, "labels": labels}


@app.post("/projects/{project_id}/labels")
def create_project_labels(project_id: str, labels: List[str], db: Session = Depends(get_db)):
    # Validate that project_id is a valid UUID
    try:
        uuid.UUID(project_id)
    except:
        return JSONResponse(
            status_code=400,
            content={"message": "Project ID " + project_id + " is not a valid UUID"},
        )

    res = crud.get_project_by_id(db, project_id)

    if res == None:
        return JSONResponse(
            status_code=404,
            content={"message": "Project with ID " + project_id + " not found"},
        )

    new_labels = [schemas.LabelCreate.parse_obj(
                    {"project_id": project_id, "name": str(label_name)}
                ) for label_name in labels]
    crud.insert_labels(db, new_labels)

    return 200


@app.get("/projects/{project_id}/labeled-images")
def get_project_labeled_images(project_id: str):
    # TODO: use project_id to retrieve all annotated images
    # contains (bounding boxes and class labels) for all
    # frames from this project

    return {"id": project_id, "labeled-images": []}


@app.get("/projects/{project_id}/videos")
def get_project_videos(project_id: str, db: Session = Depends(get_db)):
    # Validate that project_id is a valid UUID
    try:
        uuid.UUID(project_id)
    except:
        return JSONResponse(
            status_code=400,
            content={"message": "Project ID " + project_id + " is not a valid UUID"},
        )

    res = crud.get_project_by_id(db, project_id)

    if res == None:
        return JSONResponse(
            status_code=404,
            content={"message": "Project with ID " + project_id + " not found"},
        )

    rows_returned = crud.get_videos_by_project_id(db, project_id)
    videos = []
    for row in rows_returned:
        # Convert from database query response model to response model
        video = schemas.VideoResponse.parse_obj(
            {
                "id": row.id,
                "project_id": row.project_id,
                "name": row.name,
                "date_uploaded": row.date_uploaded,
                "percent_labeled": calculate_percent_frames_reviewed(row),
                "number_of_frames": len(row.frames),
                "preprocessing_status": row.preprocessing_status,
            }
        )
        videos.append(video)

    return {"project_id": project_id, "videos": videos}


@app.post("/projects/{project_id}/videos")
async def upload_project_video(
    project_id: str,
    video: UploadFile,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    # Validate that project_id is a valid UUID
    try:
        uuid.UUID(project_id)
    except:
        return JSONResponse(
            status_code=400,
            content={"message": "Project ID " + project_id + " is not a valid UUID"},
        )

    # Validate that the specified project exists in the database
    containing_project = crud.get_project_by_id(db, project_id)
    if containing_project == None:
        return JSONResponse(
            status_code=404,
            content={"message": "Project with ID " + project_id + " not found"},
        )

    # Validate that the video has not already been uploaded
    duplicate_video = crud.get_video_by_name(db, video.filename)
    if duplicate_video:
        return JSONResponse(
            status_code=400,
            content={
                "message": "Video "
                + video.filename
                + " has already been uploaded to project with ID "
                + str(duplicate_video.project_id)
            },
        )

    # Validate that the video file is in fact a video
    if video.content_type != "video/mp4":
        return JSONResponse(
            status_code=400,
            content={
                "message": "Video "
                + video.filename
                + " is not of content-type video/mp4"
            },
        )

    # Read the video file
    try:
        # Read video data as bytes
        contents = video.file.read()
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "message": "Failed to read video "
                + video.filename
                + " with error "
                + str(e)
            },
        )

    project_name = containing_project.name
    video_name = video.filename.replace(".mp4", "")

    # Create default save location
    local_save_path = os.getcwd() + "/local_projects/" + project_name + "/" + video_name
    storage_location = {
        "azure": False,
        "path": local_save_path + "/frames",
        "container": "",
    }

    # Upload video to the appropriate storage location (Azure or local file system)
    try:
        if blob_service_client:
            # If connected to Azure, upload video to project's blob storage container
            # under the path video_name/video.mp4
            # The storage container is already named after the project
            blob_client = blob_service_client.get_blob_client(
                container=project_name, blob=video_name + "/" + video.filename
            )
            blob_client.upload_blob(contents)

            # Set up appropriate information for saving extracted frames in Azure
            storage_location["azure"] = True
            storage_location["container"] = project_name
            storage_location["path"] = video_name + "/frames"
        else:
            # Otherwise, add to project directory in the local file system

            # If project_name/video_name/frames directories don't exist, create them
            if not os.path.exists(storage_location["path"]):
                os.makedirs(storage_location["path"])

            # Save the video file
            video_save_path = local_save_path + video.filename
            if not os.path.exists(video_save_path):
                with open(video_save_path, "wb") as f:
                    f.write(contents)

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "message": "Failed to save video "
                + video.filename
                + " with error "
                + str(e)
            },
        )

    try:
        # Insert new video into database
        video_obj = schemas.VideoCreate.parse_obj(
            {"name": video.filename, "project_id": containing_project.id}
        )
        video_insert_response = crud.create_video(db, video_obj)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "message": "Failed to insert video "
                + video.filename
                + " into database with error "
                + str(e)
            },
        )

    # Preprocess the video as a background task
    background_tasks.add_task(
        preprocess_video,
        contents,
        storage_location,
        video_insert_response.id,
        project_id,
        db,
    )

    # Close the video file
    video.file.close()

    return JSONResponse(
        status_code=202,
        content={"id": project_id, "video_id": str(video_insert_response.id)},
    )


###############################################################
# Videos endpoints
###############################################################


@app.get("/videos/{video_id}", response_model=schemas.VideoResponse)
def get_video(video_id: str, db: Session = Depends(get_db)):
    # Validate that video_id is a valid UUID
    try:
        uuid.UUID(video_id)
    except:
        return JSONResponse(
            status_code=400,
            content={"message": "Video ID " + video_id + " is not a valid UUID"},
        )

    res = crud.get_video_by_id(db, video_id)

    if res == None:
        return JSONResponse(
            status_code=404,
            content={"message": "Video with ID " + video_id + " not found"},
        )

    # Convert from database query response model to response model
    video = schemas.VideoResponse.parse_obj(
        {
            "id": res.id,
            "project_id": res.project_id,
            "name": res.name,
            "date_uploaded": res.date_uploaded,
            "percent_labeled": calculate_percent_frames_reviewed(res),
            "number_of_frames": len(res.frames),
            "preprocessing_status": res.preprocessing_status,
        }
    )

    return video


@app.get("/videos/{video_id}/preprocess")
def restart_video_preprocess(
    video_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    # Validate that video_id is a valid UUID
    try:
        uuid.UUID(video_id)
    except:
        return JSONResponse(
            status_code=400,
            content={"message": "Video ID " + video_id + " is not a valid UUID"},
        )

    video = crud.get_video_by_id(db, video_id)

    if video == None:
        return JSONResponse(
            status_code=404,
            content={"message": "Video with ID " + video_id + " not found"},
        )

    if video.preprocessing_status == "success":
        return JSONResponse(
            status_code=200,
            content={
                "message": "Video with ID "
                + video_id
                + " has already been successfully preprocessed"
            },
        )

    project = crud.get_project_by_id(db, video.project_id)
    video_name = video.name.replace(".mp4", "")
    local_save_path = os.getcwd() + "/local_projects/" + project.name + "/" + video_name
    storage_location = {
        "azure": False,
        "path": local_save_path + "/frames",
        "container": "",
    }

    # Get the video's content as bytes (either from local storage or Azure)
    try:
        if blob_service_client:
            # If connected to Azure, download the video as a byte stream
            blob_client = blob_service_client.get_blob_client(
                container=project.name, blob=video_name + "/" + video.name
            )
            contents = BytesIO()
            blob_client.download_blob().readinto(contents)

            # Set up appropriate information for saving extracted frames in Azure
            storage_location["azure"] = True
            storage_location["container"] = project.name
            storage_location["path"] = video_name + "/frames"
        else:
            # Otherwise, read as bytes from the local video file
            video_save_path = local_save_path + video.name
            with open(video_save_path, "rb") as f:
                contents = f.read()

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "message": "While restarting preprocessing, failed to fetch video "
                + video.name
                + " with error "
                + str(e)
            },
        )

    # Preprocess the video as a background task
    background_tasks.add_task(
        preprocess_video,
        contents,
        storage_location,
        video_id,
        video.project_id,
        db,
    )

    return JSONResponse(
        status_code=202,
        content={"id": str(video.project_id), "video_id": str(video.id)},
    )


@app.delete("/videos/{video_id}")
def delete_video(video_id: str):
    # TODO: delete requested video and all associated
    # artifacts (bounding boxes, images, numpy files)

    # TODO: return status code from SQL delete operation
    return 200


@app.get("/videos/{video_id}/frames")
def get_video_frames(video_id: str, db: Session = Depends(get_db)):
    # Validate that video_id is a valid UUID
    try:
        uuid.UUID(video_id)
    except:
        return JSONResponse(
            status_code=400,
            content={"message": "Video ID " + video_id + " is not a valid UUID"},
        )

    res = crud.get_video_by_id(db, video_id)

    if res == None:
        return JSONResponse(
            status_code=404,
            content={"message": "Video with ID " + video_id + " not found"},
        )

    video_frames = crud.get_frames_by_video_id(db, video_id)
    labels_per_frame = crud.get_unique_labels_per_frame(db, video_id)

    # Create a mapping from frame ID to list of unique labels detected in
    # that frame that the next for loop can reference
    labels_per_frame_dict = {}
    for frame_id, labels in labels_per_frame:
        labels_per_frame_dict[frame_id] = [] if labels == [None] else labels

    frames = []
    for frame in video_frames:
        # Convert from database query response model to response model
        parsed_frame = schemas.Frame.parse_obj(
            {
                "id": frame.id,
                "human_reviewed": frame.human_reviewed,
                "width": frame.width,
                "height": frame.height,
                "project_id": frame.project_id,
                "video_id": frame.video_id,
                "frame_url": frame.frame_url,
                "labels": labels_per_frame_dict[frame.id],
            }
        )
        frames.append(parsed_frame)

    return {"video_id": video_id, "frames": frames}


###############################################################
# Frames endpoints
###############################################################


# Get the bounding boxes for this frame
@app.get("/frames/{frame_id}/inferences")
def get_frame_inferences(frame_id: str, db: Session = Depends(get_db)):
    try:
        uuid.UUID(frame_id)
    except:
        return JSONResponse(
            status_code=400,
            content={"message": "Frame ID " + frame_id + " is not a valid UUID"},
        )

    res = crud.get_frame_by_id(db, frame_id)

    if res == None:
        return JSONResponse(
            status_code=404,
            content={"message": "Frame with ID " + frame_id + " not found"},
        )

    rows_returned = crud.get_boxes_by_frame_id(db, frame_id)

    boxes = []
    for row in rows_returned:
        box = schemas.BoundingBox.parse_obj(
            {
                "x_top_left": row.x_top_left,
                "y_top_left": row.y_top_left,
                "x_bottom_right": row.x_bottom_right,
                "y_bottom_right": row.y_bottom_right,
                "width": row.width,
                "height": row.height,
                "frame_id": frame_id,
                "label_id": row.label_id,
                "id": row.id,
                "prediction": row.prediction,
            }
        )
        boxes.append(box)

    return {"frame_id": frame_id, "bounding_boxes": boxes}


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
                "height": 200,
            }
        ],
    }


@app.put("/frames")
async def update_frames(
    updated_frames: List[schemas.Frame],
    db: Session = Depends(get_db),
):
    # Save the updated frames information
    result = crud.update_frames(db, updated_frames)
    if dict(result) != {}:
        return 500
    return 200


###############################################################
# Bounding Boxes endpoints
###############################################################


@app.post("/boundingboxes")
async def update_bounding_boxes(
    project_id: str,
    video_id: str,
    updated_boxes: List[schemas.BoundingBox],
    db: Session = Depends(get_db),
):
    # Validate that project_id is a valid UUID
    try:
        uuid.UUID(project_id)
    except:
        return JSONResponse(
            status_code=400,
            content={"message": "Project ID " + project_id + " is not a valid UUID"},
        )

    res = crud.get_project_by_id(db, project_id)

    if res == None:
        return JSONResponse(
            status_code=404,
            content={"message": "Project with ID " + project_id + " not found"},
        )

    # Validate that video_id is a valid UUID
    try:
        uuid.UUID(video_id)
    except:
        return JSONResponse(
            status_code=400,
            content={"message": "Video ID " + video_id + " is not a valid UUID"},
        )

    res = crud.get_video_by_id(db, video_id)

    if res == None:
        return JSONResponse(
            status_code=404,
            content={"message": "Video with ID " + video_id + " not found"},
        )

    # Save the updated bounding box information
    result = crud.update_boxes(db, updated_boxes)
    if dict(result) != {}:
        return 500

    # Find out the specific labels used within this project
    project_labels = crud.get_labels_by_project(db, project_id)
    label2id = {label.name: label.id for label in project_labels}
    unique_labels = list(label2id.keys())

    # Fetch image_features and label names for each box for each
    # frame in a video (the one specified in updated_boxes)
    all_boxes = crud.get_box_vectors_and_labels_by_video_id(db, video_id)
    box_vectors = []
    box_labels = []
    unreviewed_boxes = []
    for row in all_boxes:
        box = row[0]
        box_vectors.append(box.image_features)
        box_labels.append(row.name)
        if box.prediction == True:
            unreviewed_boxes.append(box)

    # Instantiate a new classification model (small, feed forward network)
    # input_dim=128*128*3 ?
    model = ClassifierManager(box_vectors, box_labels, unique_labels)

    # Train the model using all of the bounding box information
    model.fit()

    if len(unreviewed_boxes) > 0:
        # Get new label predictions for each box
        unreviewed_boxes_vectors = [box.image_features for box in unreviewed_boxes]
        new_predictions = model.predict(unreviewed_boxes_vectors)

        # Attach the new label predictions to each box
        new_predicted_boxes = []
        for updated_label, box in zip(new_predictions, unreviewed_boxes):
            new_box = schemas.BoundingBox.parse_obj(
                {
                    "x_top_left": box.x_top_left,
                    "y_top_left": box.y_top_left,
                    "x_bottom_right": box.x_bottom_right,
                    "y_bottom_right": box.y_bottom_right,
                    "width": box.width,
                    "height": box.height,
                    "frame_id": box.frame_id,
                    "label_id": label2id[updated_label],
                    "id": box.id,
                    "prediction": True,
                }
            )
            new_predicted_boxes.append(new_box)

        # Save updated label predictions in the database
        result = crud.update_boxes(db, new_predicted_boxes)
        if dict(result) != {}:
            return 500

    # Let the client know everything went well and to proceed
    return 200


@app.put("/boundingboxes")
def update_boxes_without_inference(
    updated_boxes: List[schemas.BoundingBox], db: Session = Depends(get_db)
):
    # Save the updated bounding box information
    result = crud.update_boxes(db, updated_boxes)
    if dict(result) != {}:
        return 500
    return 200
