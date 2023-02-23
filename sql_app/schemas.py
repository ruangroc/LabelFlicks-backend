from typing import List, Union
from uuid import UUID
from datetime import date

from pydantic import BaseModel

# Define all Pydantic models that define valid data shapes for the API

# This setting makes it possible for the Pydantic models to read
# information from the SQLAlchemy ORM models
# class Config:
#     orm_mode = True

###############################################################
# Project schemas
###############################################################

# Base class for attributes shared between creating and reading
class ProjectBase(BaseModel):
    name: str
    frame_extraction_rate: Union[int, None] = 1 # optional
    percent_labeled: Union[float, None] = 0.0
    video_count: Union[int, None] = 0

# When creating a project, we won't know its uuid
class ProjectCreate(ProjectBase):
    pass

# When fetching a project, we should know everything
class Project(ProjectBase):
    id: UUID 

    class Config:
        orm_mode = True


###############################################################
# Video schemas
###############################################################

# Base class for attributes shared between creating and reading
class VideoBase(BaseModel):
    name: str
    project_id: UUID
    

# When uploading a video, we won't know its id, frame features url,
# similarity url, video url, or current date
class VideoCreate(VideoBase):
    pass

# When fetching a video, we should know everything
class Video(VideoBase):
    id: UUID
    project_id: UUID
    name: str
    video_url: str
    frame_features_url: str
    frame_similarity_url: str
    date_uploaded: date

    class Config:
        orm_mode = True


###############################################################
# Frame schemas
###############################################################

# Base class for attributes shared between creating and reading
class FrameBase(BaseModel):
    human_reviwed: bool = False
    width: int
    height: int
    project_id: UUID
    video_id: UUID
    frame_url: str

# When uploading a frame, we should know what project it belongs
# to, what video it came from, and frame_url can simply be some
# incrementing int
class FrameCreate(FrameBase):
    pass

# When fetching a frame, we should know everything
class Frame(FrameBase):
    id: UUID

    class Config:
        orm_mode = True
    

###############################################################
# BoundingBox schemas
###############################################################

# Base class for attributes shared between creating and reading
class BoundingBoxBase(BaseModel):
    x_top_left: int
    y_top_left: int
    x_bottom_right: int
    y_bottom_right: int
    width: int
    height: int
    frame_id: UUID
    label_id: UUID

# We should know everything about a new BoundingBox
# except for the auto-generated UUID
class BoundingBoxCreate(BoundingBoxBase):
    pass

# When fetching a bounding box, we should know everything
class BoundingBox(BoundingBoxBase):
    id: UUID

    class Config:
        orm_mode = True

###############################################################
# Label schemas
###############################################################

# Base class for attributes shared between creating and reading
class LabelBase(BaseModel):
    name: str
    project_id: UUID

# When creating a label, we won't know its uuid
class ProjectCreate(ProjectBase):
    pass

# When fetching a label, we should know everything
class Project(ProjectBase):
    id: UUID

    class Config:
        orm_mode = True