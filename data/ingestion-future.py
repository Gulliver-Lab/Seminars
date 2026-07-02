import datetime
from typing import get_args

import pandas as pd

import seminars


def parse_person(person_str: str) -> list[seminars.models.PERSONS]:
    if "/" in person_str:
        persons = [x.strip() for x in person_str.split("/")]
    else:
        persons = [person_str.strip()]

    if persons == ["Alice"]:
        persons = [""]

    possible_values = get_args(seminars.models.PERSONS)
    for person in persons:
        if person not in possible_values:
            raise ValueError(f"Wrong person {person}")

    return persons


if __name__ == "__main__":
    df = pd.read_csv("future.csv")
    df = df.fillna("")

    possible_topics = get_args(seminars.models.ResearchTopic)

    speakers = []
    for _, row in df.iterrows():
        topic = row["topic"].strip().title()
        if topic == "Biophys":
            topic = "BioPhys"

        if topic not in possible_topics:
            raise ValueError(f"Wrong topic {topic}")

        speakers.append(
            seminars.Speaker(
                name=row["name"],
                affiliation=row["affiliation"],
                email="",
                topic=topic,
                contact_persons=parse_person(row["person"]),
                notes=row["comments"],
                want_to_invite=True,
            )
        )

    connection = seminars.open_or_create_db("test.db")
    for speaker in speakers:
        seminars.insert_speaker(connection, speaker)
