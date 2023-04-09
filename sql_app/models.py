from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Uuid, Date, text, UUID
from sqlalchemy.orm import relationship

from .database import Base

# Define all SQLAlchemy ORM models that represent the database

class Project(Base):
    __tablename__ = "projects"

    # Represents the columns in the projects table
    id = Column('id', Uuid, primary_key=True, index=True, unique=True, server_default=text("gen_random_uuid()"))
    name = Column('name', String, unique=True)

    # Fetch the items from the database that has foreign key pointing
    # to this record in the projects table
    videos = relationship("Video", back_populates="project")
    frames = relationship("Frame", back_populates="project")
    labels = relationship("Label", back_populates="project")


class Video(Base):
    __tablename__ = "videos"

    id = Column('id', Uuid, primary_key=True, index=True, unique=True, server_default=text("gen_random_uuid()"))
    name = Column('name', String, unique=True)
    video_url = Column('video_url', String)
    frame_features_url = Column('frame_features_url', String)
    frame_similarity_url = Column('frame_similarity_url', String)
    date_uploaded = Column('date_uploaded', Date)
    project_id = Column('project_id', Uuid, ForeignKey("projects.id"))

    project = relationship("Project", back_populates="videos")
    frames = relationship("Frame", back_populates="video")


class Frame(Base):
    __tablename__ = "frames"

    id = Column('id', Uuid, primary_key=True, index=True, unique=True, server_default=text("gen_random_uuid()"))
    human_reviewed = Column('human_reviewed', Boolean)
    width = Column('width', Integer)
    height = Column('height', Integer)
    frame_url = Column('frame_url', String)
    project_id = Column('project_id', Uuid, ForeignKey("projects.id"))
    video_id = Column('video_id', Uuid, ForeignKey("videos.id"))

    project = relationship("Project", back_populates="frames")
    video = relationship("Video", back_populates="frames")


class BoundingBox(Base):
    __tablename__ = "bounding_boxes"

    id = Column('id', Uuid, primary_key=True, index=True, unique=True, server_default=text("gen_random_uuid()"))
    x_top_left = Column('x_top_left', Integer)
    y_top_left = Column('y_top_left', Integer)
    x_bottom_right = Column('x_bottom_right', Integer)
    y_bottom_right = Column('y_bottom_right', Integer)
    width = Column('width', Integer)
    height = Column('height', Integer)
    frame_id = Column('frame_id', Uuid, ForeignKey("frames.id"))
    label_id = Column('label_id', Uuid, ForeignKey("labels.id"))


class Label(Base):
    __tablename__ = "labels"

    id = Column('id', Uuid, primary_key=True, index=True, unique=True, server_default=text("gen_random_uuid()"))
    name = Column('name', String, unique=True)
    project_id = Column('project_id', Uuid, ForeignKey("projects.id"))

    project = relationship("Project", back_populates="labels")
    