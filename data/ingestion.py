import pandas as pd

import seminars


def normalize_name(name: str) -> str:
    name = name.replace("√ß", "ç")
    name = name.replace("√™", "ê")
    name = name.replace("√´", "ë")
    name = name.replace("√∂", "ö")
    name = name.replace("√Ü", "ß")
    name = name.replace("√Æ", "ï")
    name = name.replace("√º", "ü")
    return name.title()


if __name__ == "__main__":
    df = pd.read_csv(
        "2006-2024.csv", names=["name", "date"] + [str(i) for i in range(10)]
    )
    df.dropna(subset="name", inplace=True)

    # Handle characters that were not processed properly
    df["name"] = df["name"].apply(normalize_name)

    speakers = []
    for _, row in df.iterrows():
        name = row["name"]

        # Skip some edge cases
        if name in [
            "2008",
            "2009",
            "2010",
            "Name",
            "2011",
            "2012",
            "2013",
            "2014",
            "2015",
            "2016",
            "2017",
            "2018",
            "2019",
            "2020",
            "2021",
            "2022",
            "2023",
            "2024",
        ]:
            continue
        if "Chaire" in name or "Remplacement" in name:
            continue
        if len(name) > 100:
            continue

        speakers.append(
            seminars.Speaker(
                name=name,
                affiliation="",
                email="",
                topic="",
                contact_persons=[""],
                notes="Imported from drive",
                exclude=False,
            )
        )

    connection = seminars.open_or_create_db("test.db")
    for speaker in speakers:
        seminars.insert_speaker(connection, speaker)
