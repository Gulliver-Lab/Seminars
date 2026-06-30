import dataclasses
import datetime


@dataclasses.dataclass
class Speaker:
    name: str
    affiliation: str
    email: str
    topic: str
    contact_persons: list[str]
    notes: str
    exclude: bool


@dataclasses.dataclass
class Talk:
    date: datetime.datetime
    speaker: str
    title: str
    abstract: str
    status: str
    comments: str
