from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

load_dotenv()

SQLALCHEMY_DATABASE_URL = ""

# Get the correct database URL depending on the environment
if os.getenv('TEST_ENVIRONMENT') == "TRUE":
    SQLALCHEMY_DATABASE_URL = os.getenv("POSTGRES_TEST_DATABASE_URL")
else:
    SQLALCHEMY_DATABASE_URL = os.getenv("POSTGRES_DEV_DATABASE_URL")

engine = create_engine(SQLALCHEMY_DATABASE_URL)

# each instance of SessionLocal class will be a database session
# not the same as SQLAlchemy's Session class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# inherit from this Base class to create ORM models that represent the database
Base = declarative_base()

