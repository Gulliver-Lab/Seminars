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

    df_existing_speakers = seminars.read_speakers(connection)

    # 2026 talks
    df = pd.read_csv("2026-talks.csv")
    df = df.fillna("")
    df["speaker"] = df["speaker"].apply(lambda x: x.strip().title())

    # Add speakers not in DB
    speakers = []
    for _, row in df[df["speaker"] != ""].iterrows():
        name = row["speaker"]
        if name not in list(df_existing_speakers["name"]):
            speakers.append(
                seminars.Speaker(
                    name=name,
                    affiliation="",
                    email="",
                    topic="Other",
                    contact_persons=parse_person(row["contacts"]),
                    notes="",
                    want_to_invite=True,
                )
            )
    for speaker in speakers:
        seminars.insert_speaker(connection, speaker)

    # Parse the talks
    talks = []
    for _, row in df.iterrows():
        date = datetime.datetime.strptime("2026/" + row["date"], "%Y/%d/%m")
        status = (
            seminars.TalkStatus.COMPLETED
            if row["confirmed"] == "x"
            else seminars.TalkStatus.PLANNED
        )

        talks.append(
            seminars.Talk(
                date=date,
                speaker=row["speaker"],
                title="",
                abstract="",
                status=status,
                comments=row["comment"],
                organizer=row["organizer"],
            )
        )

    # Add a talk event for each week in july/august
    summer_mondays = [
        "2026-07-06",
        "2026-07-13",
        "2026-07-20",
        "2026-07-27",
        "2026-08-03",
        "2026-08-10",
        "2026-08-17",
        "2026-08-24",
        "2026-08-31",
    ]
    talks.extend(
        [
            seminars.Talk(
                date=datetime.datetime.strptime(x, "%Y-%m-%d"),
                speaker="",
                title="",
                abstract="",
                status=seminars.TalkStatus.COMPLETED,
                comments="Summer",
            )
            for x in summer_mondays
        ]
    )

    speaker = seminars.Speaker(
        name="",
        affiliation="",
        email="",
        topic="Other",
        contact_persons=[""],
        notes="Placeholder for talks with no speakers",
        want_to_invite=False,
    )
    seminars.insert_speaker(connection, speaker)

    for talk in talks:
        seminars.insert_talk(connection, talk)
