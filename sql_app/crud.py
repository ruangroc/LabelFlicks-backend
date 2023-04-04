from sqlalchemy.orm import Session
from sqlalchemy import Uuid

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
    db_project = models.Project(name=project.name, )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

# GET /projects/{project_id}
def get_project_by_id(db: Session, project_id: Uuid):
    return db.query(models.Project).filter(models.Project.id == project_id).first()

def get_project_by_name(db: Session, project_name: Uuid):
    return db.query(models.Project).filter(models.Project.name == project_name).first()

# Get percent of frames that have been human-reviewed
def get_percent_frames_reviewed(db: Session, project_id: Uuid):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    
    # If no frames exist in the project, no need to calculate percent reviewed
    total = len(project.frames)
    if total == 0:
        return 0.0
    
    reviewed = 0
    for i in range(total):
        if project.frames[i].human_reviewed:
            reviewed += 1
    return round(100*(reviewed / total), 2)

# Get number of videos in this project
def get_video_count(db: Session, project_id: Uuid):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    return len(project.videos)

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
        name=video.name, 
        project_id=video.project_id,
        date_uploaded=current_date
    )
    db.add(db_video)
    db.commit()
    db.refresh(db_video)
    return db_video

def get_video_by_name(db: Session, video_name: str):
    return db.query(models.Video).filter(models.Video.name == video_name).first()

def get_videos_by_project_id(db: Session, project_id: Uuid):
    return db.query(models.Video.id).filter(models.Video.project_id == project_id).all()

def get_video_by_id(db: Session, video_id: Uuid):
    return db.query(models.Video).filter(models.Video.id == video_id).first()

def get_video_frames_count(db: Session, video_id: Uuid):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    return len(video.frames)

def get_video_percent_frames_reviewed(db: Session, video_id: Uuid):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()

    # If no frames exist for this video, no need to calculate percent reviewed
    total = len(video.frames)
    if total == 0:
        return 0.0
    
    reviewed = 0
    for i in range(total):
        if video.frames[i].human_reviewed:
            reviewed += 1
    return round(100*(reviewed / total), 2)


###############################################################
# frames table
###############################################################

###############################################################
# bounding_boxes table
###############################################################

###############################################################
# labels table
###############################################################

