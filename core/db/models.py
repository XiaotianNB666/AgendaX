from sqlmodel import SQLModel, Field
from typing import Optional


class BaseModel(SQLModel):
    pass


class AssignmentTable(BaseModel, table=True):
    __tablename__ = "AssignmentTable"

    id: Optional[int] = Field(default=None, primary_key=True)
    subject: str
    data_type: str
    data: str
    start_time: float
    finish_time: Optional[float] = None
    finish_time_type: str = ""


class AssignmentRecord(BaseModel, table=True):
    __tablename__ = "AssignmentRecord"

    id: Optional[int] = Field(default=None, primary_key=True)
    subject: str
    data_type: str
    data: str
    start_time: float
    finish_time: Optional[float] = None
    finish_time_type: str = ""


class ExerciseSubjectTable(BaseModel, table=True):
    __tablename__ = "ExerciseSubjectTable"

    exercise: str = Field(primary_key=True)
    subject: str = Field(primary_key=True)
