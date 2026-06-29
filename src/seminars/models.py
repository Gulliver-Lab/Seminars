import dataclasses


@dataclasses.dataclass
class Speaker:
    name: str
    affiliation: str
    email: str
    topic: str
    contact_persons: list[str]
    notes: str
    exclude: bool
