from typing import List
from uuid import UUID
from datetime import date

from pydantic import BaseModel

import numpy as np
import torch

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

# When creating a project, we won't know its uuid
class ProjectCreate(ProjectBase):
    pass

# When fetching a project, we should know everything
class ExistingProject(ProjectBase):
    id: UUID 
    percent_labeled: float = 0.0
    video_count: int = 0

    class Config:
        orm_mode = True
        allow_mutation = True


###############################################################
# Video schemas
###############################################################

# Base class for attributes shared between creating and reading
class VideoBase(BaseModel):
    name: str
    project_id: UUID
    

# When uploading a video, we won't know its id, url, or current date
class VideoCreate(VideoBase):
    pass

# When fetching a video, we should know everything
class Video(VideoBase):
    id: UUID
    project_id: UUID
    name: str
    video_url: str
    date_uploaded: date
    preprocessing_status: str

    class Config:
        orm_mode = True

# What we want to return to the client
class VideoResponse(VideoBase):
    id: UUID
    project_id: UUID
    name: str
    date_uploaded: date
    percent_labeled: float
    number_of_frames: int
    preprocessing_status: str
    

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
    image_features: bytes

class BoundingBox(BoundingBoxBase):
    id: UUID

    class Config:
        orm_mode = True


# ORM configured class can't be used to receive client requests: https://stackoverflow.com/a/70845083
# Hence the two below classes
# class UpdatedBoundingBox(BoundingBoxBase):
#     id: UUID

# class BoundingBox(UpdatedBoundingBox):
#     class Config:
#         orm_mode = True

###############################################################
# Label schemas
###############################################################

# Base class for attributes shared between creating and reading
class LabelBase(BaseModel):
    name: str
    project_id: UUID

# When creating a label, we won't know its uuid
class LabelCreate(LabelBase):
    pass

# When fetching a label, we should know everything
class Label(LabelBase):
    id: UUID

    class Config:
        orm_mode = True


###############################################################
# Frame schemas
###############################################################

# Base class for attributes shared between creating and reading
class FrameBase(BaseModel):
    human_reviewed: bool = False
    width: int
    height: int
    project_id: UUID
    video_id: UUID
    frame_url: str

# When uploading a frame, we should know what project it belongs
# to, what video it came from, and where it's stored
class FrameCreate(FrameBase):
    pass

# When fetching a frame, we should know everything
class Frame(FrameBase):
    id: UUID
    labels: List[UUID]

    class Config:
        orm_mode = True