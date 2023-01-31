from typing import Union
from fastapi import FastAPI
from pydantic import BaseModel

###############################################################
# Data classes for post request bodies
###############################################################

class Project(BaseModel):
    name: str
    frame_extraction_rate: Union[int, None] = None # optional


# create FastAPI instance
app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}

# q = query parameters
@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


###############################################################
# Projects endpoints
###############################################################

@app.get("/projects")
def get_all_projects():
    # TODO: retrieve projects from database, requires 
    # calculating percent_labeled for each

    return {
        "projects": [
            {
                "id": "uuid-p1",
                "name": "raccoon-sightings",
                "frame_extraction_rate": 1,
                "percent_labeled": 50
            },
            {
                "id": "uuid-p2",
                "name": "squirrels",
                "frame_extraction_rate": 2,
                "percent_labeled": 22
            },
            {
                "id": "uuid-p3",
                "name": "cats-in-windows",
                "frame_extraction_rate": 1,
                "percent_labeled": 0
            }
        ]
    } 


@app.post("/projects")
async def create_project(project: Project):
    # TODO: validate frame_extraction rate is in expected range,
    # and later the UI can also help enforce that,
    # else default to 1 frame per second extraction rate

    # TODO: insert new project into database and return 
    # with id and percent_labeled fields extracted
    return project


@app.get("/projects/{project_id}")
def get_project(project_id: str):
    # TODO: use project_id to retrieve the project from the 
    # database, or return an error message

    return {"project": {
            "id": project_id,
            "name": "requested-project-name",
            "frame_extraction_rate": 1,
            "percent_labeled": 10
        }
    }


@app.put("/projects/{project_id}")
async def rename_project(project_id: str, project: Project):
    # TODO: use project_id to update name of the project,
    # or return error for invalid id
    
    return {"project": {
            "id": project_id,
            "name": project["name"],
            "frame_extraction_rate": 1,
            "percent_labeled": 10
        }
    }

@app.delete("/projects/{project_id}")
def delete_project(project_id: str):
    # TODO: delete requested project and all associated
    # artifacts (videos, images, numpy files)

    # TODO: return status code from SQL delete operation
    return 200


@app.get("/projects/{project_id}/labels")
def get_project_labels(project_id: str):
    # TODO: use project_id to retrieve all bounding box and 
    # class label information for all frames from this project
    # (should be exported in a common format, I think COCO)

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


###############################################################
# Videos endpoints
###############################################################


