"""Build the canonical clean course dataset.

The generated CSV is the source of truth for future retrieval, ranking, API, and
evaluation work. Raw Kaggle files are read-only inputs.
"""

from __future__ import annotations

import hashlib
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

try:
    from ftfy import fix_text
except ImportError:  # pragma: no cover - local fallback if ftfy is unavailable.
    fix_text = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT.parent / "Kaggle-Dataset"
OUTPUT_PATH = PROJECT_ROOT / "data" / "clean_courses.csv"

V2_PATH = RAW_DATA_DIR / "coursera_course_dataset_v2_no_null.csv"
V3_PATH = RAW_DATA_DIR / "coursera_course_dataset_v3.csv"

DIFFICULTY_ORDER = {
    "Beginner": 1,
    "Intermediate": 2,
    "Mixed": 2,
    "Advanced": 3,
}

MOJIBAKE_REPLACEMENTS = {
    "Â·": "·",
    "Â©": "©",
    "Â®": "®",
    "Â": "",
    "â€™": "'",
    "â€˜": "'",
    "â€œ": '"',
    "â€�": '"',
    "â€“": "-",
    "â€”": "-",
    "â€¦": "...",
    "â€¢": "-",
    "â€": '"',
}

DESCRIPTION_STOPWORDS = {
    "about",
    "advanced",
    "and",
    "course",
    "data",
    "for",
    "from",
    "google",
    "introduction",
    "intro",
    "learn",
    "learning",
    "the",
    "with",
    "your",
}


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8")


def clean_text(value: object) -> str:
    """Normalize text while preserving multilingual course titles."""
    if pd.isna(value):
        return ""

    text = str(value)
    if fix_text is not None:
        text = fix_text(text)

    for broken, replacement in MOJIBAKE_REPLACEMENTS.items():
        text = text.replace(broken, replacement)

    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalized_key(title: object, organization: object) -> str:
    return f"{clean_text(title).casefold()}|{clean_text(organization).casefold()}"


def stable_course_id(title: str, organization: str) -> str:
    readable = re.sub(r"[^a-z0-9]+", "-", f"{title}-{organization}".casefold())
    readable = readable.strip("-")[:60] or "course"
    digest = hashlib.sha1(f"{title}|{organization}".encode("utf-8")).hexdigest()[:10]
    return f"{readable}-{digest}"


def parse_count(value: object) -> pd.NA | int:
    """Parse values such as '20K', '1.2M', or '700,909' into integers."""
    if pd.isna(value):
        return pd.NA

    text = clean_text(value).replace(",", "")
    if not text:
        return pd.NA

    match = re.fullmatch(r"(?P<number>\d+(?:\.\d+)?)(?P<suffix>[kKmM]?)", text)
    if not match:
        return pd.NA

    number = float(match.group("number"))
    suffix = match.group("suffix").lower()
    multiplier = {"": 1, "k": 1_000, "m": 1_000_000}[suffix]
    return int(number * multiplier)


def parse_v2_review_count(value: object) -> pd.NA | int:
    """Extract review count from values like '4.8(20K reviews)'."""
    text = clean_text(value)
    match = re.search(r"\((?P<count>[\d.,]+[kKmM]?)\s+reviews?\)", text)
    if not match:
        return pd.NA
    return parse_count(match.group("count"))


def clean_skills(value: object) -> list[str]:
    raw_skills = [clean_text(skill) for skill in str(value).split(",")]
    skills: list[str] = []
    seen: set[str] = set()

    for skill in raw_skills:
        if not skill:
            continue

        key = skill.casefold()
        if key in seen:
            continue

        seen.add(key)
        skills.append(skill)

    return skills


def normalize_difficulty(value: object) -> str:
    text = clean_text(value).title()
    aliases = {
        "Beginner Level": "Beginner",
        "Intermediate Level": "Intermediate",
        "Advanced Level": "Advanced",
        "Mixed Level": "Mixed",
    }
    return aliases.get(text, text or "Unknown")


def normalize_type(value: object) -> str:
    text = clean_text(value)
    aliases = {
        "Guided Projects": "Guided Project",
        "Professional Certificates": "Professional Certificate",
    }
    return aliases.get(text, text or "Unknown")


def description_status(title: str, description: str) -> str:
    if not description:
        return "missing"

    title_words = {
        word.casefold()
        for word in re.findall(r"[A-Za-z]{4,}", title)
        if word.casefold() not in DESCRIPTION_STOPWORDS
    }
    if title_words and not any(word in description.casefold() for word in title_words):
        return "suspect"

    return "available"


def build_embedding_text(row: pd.Series) -> str:
    parts = [
        f"Course title: {row['title']}",
        f"Provider: {row['organization']}",
        f"Difficulty: {row['difficulty']}",
        f"Course type: {row['course_type']}",
        f"Duration: {row['duration']}",
        f"Skills taught: {row['skills_text']}",
    ]

    if row["description_status"] == "available":
        parts.append(f"Description: {row['description']}")

    return "\n".join(part for part in parts if part and not part.endswith(": "))


def build_clean_dataset(v2: pd.DataFrame, v3: pd.DataFrame) -> pd.DataFrame:
    v2 = v2.copy()
    v3 = v3.copy()

    v2["merge_key"] = [
        normalized_key(title, organization)
        for title, organization in zip(v2["Title"], v2["Organization"])
    ]
    v3["merge_key"] = [
        normalized_key(title, organization)
        for title, organization in zip(v3["Title"], v3["Organization"])
    ]

    v2_reference = v2[
        ["merge_key", "Review counts", "Metadata"]
    ].rename(
        columns={
            "Review counts": "v2_review_count_raw",
            "Metadata": "metadata_raw",
        }
    )

    merged = v3.merge(v2_reference, on="merge_key", how="left", validate="one_to_one")

    # Drop rows that have no course description (empty or null).
    # The user requested that any course without a description be removed
    # before generating the canonical clean dataset.
    merged = merged[
        merged["course_description"].notna()
        & merged["course_description"].astype(str).str.strip().ne("")
    ].copy()

    clean = pd.DataFrame()
    clean["course_id"] = [
        stable_course_id(clean_text(title), clean_text(organization))
        for title, organization in zip(merged["Title"], merged["Organization"])
    ]
    clean["title"] = merged["Title"].map(clean_text)
    clean["organization"] = merged["Organization"].map(clean_text)
    clean["course_url"] = merged["course_url"].map(clean_text)
    clean["difficulty"] = merged["Difficulty"].map(normalize_difficulty)
    clean["difficulty_level"] = clean["difficulty"].map(DIFFICULTY_ORDER).fillna(0).astype("int64")
    clean["course_type"] = merged["Type"].map(normalize_type)
    clean["duration"] = merged["Duration"].map(clean_text)
    clean["rating"] = pd.to_numeric(merged["Ratings"], errors="coerce")
    clean["review_count"] = merged["Review Count"].map(parse_count)
    clean["review_count_from_v2"] = merged["v2_review_count_raw"].map(parse_v2_review_count)
    clean["students_enrolled"] = merged["course_students_enrolled"].map(parse_count)
    clean["description"] = merged["course_description"].map(clean_text)
    clean["metadata_raw"] = merged["metadata_raw"].map(clean_text)

    skill_lists = merged["Skills"].map(clean_skills)
    clean["skills"] = skill_lists.map(lambda skills: "|".join(skills))
    clean["skills_text"] = skill_lists.map(lambda skills: ", ".join(skills))
    clean["skill_count"] = skill_lists.map(len).astype("int64")

    clean["description_status"] = [
        description_status(title, description)
        for title, description in zip(clean["title"], clean["description"])
    ]
    clean["has_url"] = clean["course_url"].ne("")
    clean["has_description"] = clean["description"].ne("")
    clean["has_enrollment"] = clean["students_enrolled"].notna()
    clean["embedding_text"] = clean.apply(build_embedding_text, axis=1)

    clean = clean.sort_values(["title", "organization"]).reset_index(drop=True)

    int_columns = ["review_count", "review_count_from_v2", "students_enrolled"]
    for column in int_columns:
        clean[column] = clean[column].astype("Int64")

    return clean[
        [
            "course_id",
            "title",
            "organization",
            "course_url",
            "difficulty",
            "difficulty_level",
            "course_type",
            "duration",
            "rating",
            "review_count",
            "review_count_from_v2",
            "students_enrolled",
            "skills",
            "skills_text",
            "skill_count",
            "description",
            "description_status",
            "metadata_raw",
            "has_url",
            "has_description",
            "has_enrollment",
            "embedding_text",
        ]
    ]


def validate_clean_dataset(clean: pd.DataFrame) -> None:
    required_non_empty = [
        "course_id",
        "title",
        "organization",
        "difficulty",
        "course_type",
        "duration",
        "skills_text",
        "embedding_text",
    ]

    for column in required_non_empty:
        empty_count = int(clean[column].astype(str).str.strip().eq("").sum())
        if empty_count:
            raise ValueError(f"{column} has {empty_count} empty values")

    if clean["course_id"].duplicated().any():
        raise ValueError("course_id must be unique")

    if clean.duplicated(["title", "organization"]).any():
        raise ValueError("title + organization must be unique")

    if clean["rating"].isna().any():
        raise ValueError("rating contains null values")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    v2 = read_csv(V2_PATH)
    v3 = read_csv(V3_PATH)
    clean = build_clean_dataset(v2, v3)
    validate_clean_dataset(clean)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    clean.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")

    print(f"Created {OUTPUT_PATH}")
    print(f"Rows: {len(clean):,}")
    print(f"Columns: {len(clean.columns):,}")
    print("\nDescription status:")
    print(clean["description_status"].value_counts().to_string())
    print("\nMissing enrichment:")
    print(
        clean[["has_url", "has_description", "has_enrollment"]]
        .apply(lambda column: int((~column).sum()))
        .to_string()
    )


if __name__ == "__main__":
    main()
