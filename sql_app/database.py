from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# hope that's the right URL but we'll see
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:viva@localhost:5432/viva"

engine = create_engine(SQLALCHEMY_DATABASE_URL)

# each instance of SessionLocal class will be a database session
# not the same as SQLAlchemy's Session class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# inherit from this Base class to create ORM models that represent the database
Base = declarative_base()

