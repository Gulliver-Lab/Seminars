import dataclasses
import datetime
from enum import StrEnum
from typing import Literal


class TalkStatus(StrEnum):
    COMPLETED = "completed"


ResearchTopic = Literal["Active Matter", "Theory", "BioPhys", "Soft Matter", "Other"]


@dataclasses.dataclass
class Speaker:
    name: str
    affiliation: str
    email: str
    topic: ResearchTopic
    contact_persons: list[str]
    notes: str
    want_to_invite: bool


@dataclasses.dataclass
class Talk:
    date: datetime.datetime
    speaker: str
    title: str
    abstract: str
    status: TalkStatus
    comments: str
