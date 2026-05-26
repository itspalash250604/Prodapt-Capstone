"""Data quality analysis for the Coursera course datasets.

This script is intentionally read-only. It profiles the raw Kaggle CSV files so
we can design the preprocessing pipeline from evidence instead of assumptions.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterable

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT.parent / "Kaggle-Dataset"

V2_PATH = RAW_DATA_DIR / "coursera_course_dataset_v2_no_null.csv"
V3_PATH = RAW_DATA_DIR / "coursera_course_dataset_v3.csv"


def read_csv(path: Path) -> pd.DataFrame:
    """Read a CSV file with UTF-8 and preserve default pandas null handling."""
    return pd.read_csv(path, encoding="utf-8")


def text_columns(df: pd.DataFrame) -> list[str]:
    return [
        column
        for column in df.columns
        if pd.api.types.is_string_dtype(df[column]) or df[column].dtype == object
    ]


def normalized_key(df: pd.DataFrame) -> pd.Series:
    """Stable business key used to compare the two dataset versions."""
    return (
        df["Title"].astype(str).str.strip().str.casefold()
        + "|"
        + df["Organization"].astype(str).str.strip().str.casefold()
    )


def parse_count(value: object) -> int | None:
    """Parse values such as '20K', '1.2M', or '700,909' into integers."""
    if pd.isna(value):
        return None

    text = str(value).strip().replace(",", "")
    if not text:
        return None

    match = re.fullmatch(r"(?P<number>\d+(?:\.\d+)?)(?P<suffix>[kKmM]?)", text)
    if not match:
        return None

    number = float(match.group("number"))
    suffix = match.group("suffix").lower()
    multiplier = {"": 1, "k": 1_000, "m": 1_000_000}[suffix]
    return int(number * multiplier)


def print_section(title: str) -> None:
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def profile_dataset(name: str, df: pd.DataFrame) -> None:
    print_section(f"{name} BASIC PROFILE")
    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns):,}")
    print("\nColumns:")
    for column in df.columns:
        print(f"- {column}: {df[column].dtype}")

    print("\nNull values:")
    print(df.isna().sum().sort_values(ascending=False).to_string())

    print("\nBlank string values:")
    blanks = {
        column: int(df[column].astype(str).str.strip().eq("").sum())
        for column in text_columns(df)
    }
    print(pd.Series(blanks).sort_values(ascending=False).to_string())

    print("\nDuplicate checks:")
    print(f"- Full-row duplicates: {int(df.duplicated().sum()):,}")
    if {"Title", "Organization"}.issubset(df.columns):
        print(
            "- Title + Organization duplicates: "
            f"{int(df.duplicated(['Title', 'Organization']).sum()):,}"
        )


def profile_metadata(v2: pd.DataFrame, v3: pd.DataFrame) -> None:
    print_section("METADATA PROFILE")
    print("V3 difficulty distribution:")
    print(v3["Difficulty"].value_counts(dropna=False).to_string())

    print("\nV3 type distribution:")
    print(v3["Type"].value_counts(dropna=False).to_string())

    print("\nV3 duration distribution:")
    print(v3["Duration"].value_counts(dropna=False).to_string())

    print("\nV2 metadata examples:")
    print(v2["Metadata"].value_counts(dropna=False).head(20).to_string())


def profile_skills(name: str, df: pd.DataFrame) -> None:
    print_section(f"{name} SKILLS PROFILE")
    split_skills = df["Skills"].dropna().astype(str).str.split(",")
    skill_counts_per_row = split_skills.map(
        lambda values: len([value.strip() for value in values if value.strip()])
    )
    skills = split_skills.explode().astype(str).str.strip()
    skills = skills[skills.ne("")]

    print(f"Rows with skills: {len(split_skills):,}")
    print(f"Unique skill labels: {skills.nunique():,}")
    print(
        "Skills per row min/median/max: "
        f"{skill_counts_per_row.min()} / "
        f"{skill_counts_per_row.median()} / "
        f"{skill_counts_per_row.max()}"
    )
    print("\nTop 30 skill labels:")
    print(skills.value_counts().head(30).to_string())


def profile_encoding(name: str, df: pd.DataFrame) -> None:
    print_section(f"{name} ENCODING PROFILE")
    suspicious_chars = ["\u00c2", "\u00e2", "\ufffd", "\u00a0"]

    for char in suspicious_chars:
        hits: list[str] = []
        for column in text_columns(df):
            count = int(df[column].astype(str).str.contains(char, regex=False).sum())
            if count:
                hits.append(f"{column}={count}")

        label = char.encode("unicode_escape").decode("ascii")
        print(f"{label}: {', '.join(hits) if hits else 'none'}")

    non_ascii_titles = df[
        df["Title"].astype(str).str.contains(r"[^\x00-\x7F]", regex=True, na=False)
    ][["Title", "Organization"]]
    print("\nNon-ASCII title samples:")
    print(non_ascii_titles.head(20).to_string(index=False))


def profile_counts(v3: pd.DataFrame) -> None:
    print_section("NUMERIC COUNT PARSING PROFILE")

    parsed_reviews = v3["Review Count"].map(parse_count)
    parsed_enrollment = v3["course_students_enrolled"].map(parse_count)

    print("Review Count parse failures:")
    print(v3.loc[parsed_reviews.isna(), "Review Count"].value_counts(dropna=False).to_string())

    print("\nEnrollment parse failures:")
    print(
        v3.loc[
            v3["course_students_enrolled"].notna() & parsed_enrollment.isna(),
            "course_students_enrolled",
        ]
        .value_counts(dropna=False)
        .to_string()
    )

    print("\nParsed review count summary:")
    print(parsed_reviews.describe().to_string())

    print("\nParsed enrollment summary:")
    print(parsed_enrollment.describe().to_string())


def find_description_mismatches(v3: pd.DataFrame) -> pd.DataFrame:
    """Flag suspicious rows where description text does not mention title words."""
    stopwords = {
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

    rows: list[dict[str, object]] = []
    for index, row in v3.dropna(subset=["course_description"]).iterrows():
        title_words = {
            word.casefold()
            for word in re.findall(r"[A-Za-z]{4,}", str(row["Title"]))
            if word.casefold() not in stopwords
        }
        description = str(row["course_description"]).casefold()
        matched_words = sorted(word for word in title_words if word in description)

        if title_words and not matched_words:
            rows.append(
                {
                    "row_index": index,
                    "title": row["Title"],
                    "organization": row["Organization"],
                    "description_preview": re.sub(
                        r"\s+", " ", str(row["course_description"])
                    )[:180],
                }
            )

    return pd.DataFrame(rows)


def compare_versions(v2: pd.DataFrame, v3: pd.DataFrame) -> None:
    print_section("CROSS-DATASET COMPARISON")
    v2_keys = set(normalized_key(v2))
    v3_keys = set(normalized_key(v3))

    print(f"V2 rows: {len(v2):,}")
    print(f"V3 rows: {len(v3):,}")
    print(f"Overlapping Title + Organization keys: {len(v2_keys & v3_keys):,}")
    print(f"V2-only keys: {len(v2_keys - v3_keys):,}")
    print(f"V3-only keys: {len(v3_keys - v2_keys):,}")


def print_examples(title: str, values: Iterable[object], limit: int = 10) -> None:
    print_section(title)
    for value in list(values)[:limit]:
        print(f"- {value}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    v2 = read_csv(V2_PATH)
    v3 = read_csv(V3_PATH)

    profile_dataset("V2", v2)
    profile_dataset("V3", v3)
    compare_versions(v2, v3)
    profile_metadata(v2, v3)
    profile_skills("V2", v2)
    profile_skills("V3", v3)
    profile_encoding("V2", v2)
    profile_encoding("V3", v3)
    profile_counts(v3)

    mismatches = find_description_mismatches(v3)
    print_section("POTENTIAL DESCRIPTION ALIGNMENT ISSUES")
    print(f"Suspicious description/title mismatches: {len(mismatches):,}")
    print(mismatches.head(25).to_string(index=False))

    print_examples(
        "V3 ROWS WITH MISSING ENRICHMENT FIELDS",
        v3.loc[
            v3[["course_url", "course_students_enrolled", "course_description"]]
            .isna()
            .any(axis=1),
            ["Title", "Organization"],
        ].itertuples(index=False, name=None),
    )


if __name__ == "__main__":
    main()
