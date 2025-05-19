# models.py
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class PlatformType(str, Enum):
    ATCODER = "atcoder"

class SubmissionStatus(str, Enum):
    AC = "Accepted"
    WA = "Wrong Answer" 
    TLE = "Time Limit Exceeded"
    MLE = "Memory Limit Exceeded"
    RE = "Runtime Error"
    CE = "Compilation Error"
    PENDING = "Pending"

class SampleTestCase(BaseModel):
    input: str
    output: str
    explanation: Optional[str] = None

class ProblemDetailModel(BaseModel):
    title: str 
    statement: str
    constraints: str
    input_format: str
    output_format: str
    notes: Optional[str] = ""
    samples: List[SampleTestCase]
    time_limit: float
    memory_limit: int
    score: int = 100

class ProblemModel(BaseModel):
    id: str
    contest_id: str
    title: str
    url: str
    score: Optional[int] = None
    time_limit: Optional[float] = None
    memory_limit: Optional[int] = None
    content: Optional[ProblemDetailModel] = None

class ContestModel(BaseModel):
    id: str
    title: str
    start_time: datetime
    duration_minutes: int
    url: str
    problems: List[ProblemModel] = []

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "start_time": datetime.fromtimestamp(self.start_epoch_second).isoformat(),
            "duration_minutes": self.duration_second // 60,
            "rate_change": self.rate_change,
            "problems": [p.dict() for p in self.problems]
        }

class Submission(BaseModel):
    problem_id: str
    contest_id: str
    language: str
    code: str
    status: SubmissionStatus = SubmissionStatus.PENDING
    submitted_at: Optional[datetime] = None
    execution_time: Optional[float] = None
    memory_used: Optional[int] = None

class CacheInfo(BaseModel):
    last_updated: datetime
    next_update: Optional[datetime] = None
    is_stale: bool = False
