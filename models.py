from database import Base
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func

class Users(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key = True, index = True)
    username = Column(String, unique = True)
    name = Column(String)
    hashed_password = Column(String)

class Forum(Base):
    __tablename__ = "forum"

    post_id = Column(Integer, primary_key=True, index=True)
    post_body = Column(String)
    username = Column(String, ForeignKey("users.username"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Prediction(Base):
    __tablename__ = "predictions"

    pred_id = Column(Integer, primary_key=True, index=True)
    album = Column(String)
    record = Column(String)
    song = Column(String)
    artist = Column(String)
    username = Column(String, ForeignKey("users.username"))