from sqlalchemy.orm import Session
from sqlalchemy import Uuid

from . import models, schemas

import uuid

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
        frame_extraction_rate=project.frame_extraction_rate
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

# GET /projects/{project_id}
def get_project_by_id(db: Session, project_id: Uuid):
    return db.query(models.Project).filter(models.Project.id == project_id).first()

# POST /projects/{project_id}
# TODO: implement a way to rename in database

# DELETE /projects/{project_id}
# TODO: implement delete project from database


###############################################################
# videos table
###############################################################


###############################################################
# frames table
###############################################################

###############################################################
# bounding_boxes table
###############################################################

###############################################################
# labels table
###############################################################

