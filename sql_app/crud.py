from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import Uuid, String, update

from . import models, schemas

import datetime

# Define functions for executing CRUD operations on the database

###############################################################
# projects table
###############################################################


# GET /projects
def get_projects(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Project).offset(skip).limit(limit).all()


# POST /projects
def create_project(db: Session, project: schemas.ProjectCreate):
    db_project = models.Project(
        name=project.name,
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


# GET /projects/{project_id}
def get_project_by_id(db: Session, project_id: Uuid):
    return db.query(models.Project).filter(models.Project.id == project_id).first()


def get_project_by_name(db: Session, project_name: Uuid):
    return db.query(models.Project).filter(models.Project.name == project_name).first()


# POST /projects/{project_id}
# TODO: implement a way to rename in database

# DELETE /projects/{project_id}
# TODO: implement delete project from database

###############################################################
# videos table
###############################################################


# POST /projects/{project_id}/videos
def create_video(db: Session, video: schemas.VideoCreate):
    # Get local version of current date using %x format, example: 12/31/18
    current_datetime = datetime.datetime.now()
    current_date = current_datetime.strftime("%x")

    db_video = models.Video(
        name=video.name, project_id=video.project_id, date_uploaded=current_date
    )
    db.add(db_video)
    db.commit()
    db.refresh(db_video)
    return db_video


def get_video_by_name(db: Session, video_name: str):
    return db.query(models.Video).filter(models.Video.name == video_name).first()


def get_videos_by_project_id(db: Session, project_id: Uuid):
    return db.query(models.Video).filter(models.Video.project_id == project_id).all()


def get_video_by_id(db: Session, video_id: Uuid):
    return db.query(models.Video).filter(models.Video.id == video_id).first()


def set_video_preprocessing_status(db: Session, video_id: Uuid, status: String):
    stmt = (
        update(models.Video)
        .where(models.Video.id == video_id)
        .values(preprocessing_status=status)
    )
    db.execute(stmt)
    db.commit()


###############################################################
# frames table
###############################################################


def insert_frames(db: Session, frames: List[schemas.FrameCreate]):
    db_frames = [
        models.Frame(
            width=frame.width,
            height=frame.height,
            frame_url=frame.frame_url,
            project_id=frame.project_id,
            video_id=frame.video_id,
        )
        for frame in frames
    ]
    db.add_all(db_frames)
    db.commit()


def get_frames_by_video_id(db: Session, video_id: Uuid):
    return db.query(models.Frame).filter(models.Frame.video_id == video_id).all()


def get_frames_by_project_id(db: Session, project_id: Uuid):
    return db.query(models.Frame).filter(models.Frame.project_id == project_id).all()


###############################################################
# bounding_boxes table
###############################################################


def insert_boxes(db: Session, boxes: List[schemas.BoundingBoxCreate]):
    db_boxes = [
        models.BoundingBox(
            x_top_left=box.x_top_left,
            y_top_left=box.y_top_left,
            x_bottom_right=box.x_bottom_right,
            y_bottom_right=box.y_bottom_right,
            width=box.width,
            height=box.height,
            frame_id=box.frame_id,
            label_id=box.label_id,
        )
        for box in db_boxes
    ]
    db.add_all(db_boxes)
    db.commit()


###############################################################
# labels table
###############################################################


def insert_labels(db: Session, labels: List[schemas.LabelCreate]):
    db_labels = [
        models.Label(name=label.name, project_id=label.project_id) for label in labels
    ]
    db.add_all(db_labels)
    db.commit()


def get_label_by_name_and_project(db: Session, name: str, project_id: Uuid):
    return (
        db.query(models.Label)
        .filter(models.Label.name == name, models.Label.project_id == project_id)
        .first()
    )
