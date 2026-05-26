#!/usr/bin/env python3
"""
Module: profile_dataset.py
Description: Production-grade CSV Data Quality (DQ) Profiler.
             Evaluates structural integrity, type consistency, and completeness.
Author: Principal Data Engineer
"""

import os
import sys
import pandas as pd


class DataQualityProfiler:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.df = None
        self.report = {
            "critical_errors": [],
            "null_values": {},
            "type_mismatches": {},
            "duplicate_rows": 0,
            "total_rows": 0,
            "total_columns": 0
        }

    def load_data(self) -> bool:
        """Safely ingests the CSV asset and checks basic structural sanity."""
        if not os.path.exists(self.file_path):
            self.report["critical_errors"].append(f"File system error: Location '{self.file_path}' does not exist.")
            return False

        if os.path.getsize(self.file_path) == 0:
            self.report["critical_errors"].append("Structural anomaly: File is 0 bytes (empty).")
            return False

        try:
            # Low_memory=False ensures robust type inference across large blocks
            self.df = pd.read_csv(self.file_path, low_memory=False)
            self.report["total_rows"] = len(self.df)
            self.report["total_columns"] = len(self.df.columns)
            
            if self.df.empty:
                self.report["critical_errors"].append("Structural anomaly: CSV contains headers but 0 rows of data.")
                return False
            return True
        except Exception as e:
            self.report["critical_errors"].append(f"Ingestion Failure (Malformed CSV structure): {str(e)}")
            return False

    def check_completeness(self):
        """Identifies columns violating non-null invariants."""
        null_counts = self.df.isnull().sum()
        columns_with_nulls = null_counts[null_counts > 0]
        for col, count in columns_with_nulls.items():
            self.report["null_values"][col] = int(count)

    def check_type_homogeneity(self):
        """
        Scans object/string columns to find hidden type mutations.
        In pandas, mixed-type columns default to 'object'. We unpack them
        to find instances where strings, ints, and floats are mixed together.
        """
        for col in self.df.columns:
            # Map every element to its actual Python class name
            element_types = self.df[col].dropna().map(lambda x: type(x).__name__)
            unique_types = element_types.unique()

            # If a column has more than one data type co-existing, flag it
            if len(unique_types) > 1:
                type_distribution = element_types.value_counts().to_dict()
                self.report["type_mismatches"][col] = {
                    "detected_types": list(unique_types),
                    "distribution": type_distribution
                }

    def check_uniqueness(self):
        """Evaluates row-level duplication."""
        duplicate_count = self.df.duplicated().sum()
        self.report["duplicate_rows"] = int(duplicate_count)

    def execute_profile(self):
        """Pipeline orchestration loop."""
        print(f"[*] Initializing DQ scan for asset: {os.path.basename(self.file_path)}")
        
        if not self.load_data():
            self.display_report()
            return

        self.check_completeness()
        self.check_type_homogeneity()
        self.check_uniqueness()
        self.display_report()

    def display_report(self):
        """Generates clean, human-readable stdout logging based on severity."""
        print("\n" + "="*50)
        print("          DATA QUALITY ASSESSMENT REPORT          ")
        print("="*50)
        
        # 1. Critical Failures
        if self.report["critical_errors"]:
            print("\n❌ CRITICAL PIPELINE BLOCKERS:")
            for error in self.report["critical_errors"]:
                print(f"  - {error}")
            print("\n[STATUS] FAILED: Processing aborted.")
            return

        print(f"\n[INFO] Dataset Dimensions: {self.report['total_rows']} rows x {self.report['total_columns']} columns")

        # Track if any minor discrepancies were found
        clean_bill_of_health = True

        # 2. Completeness Violations
        print("\n📊 1. COMPLETENESS CHECK:")
        if self.report["null_values"]:
            clean_bill_of_health = False
            for col, count in self.report["null_values"].items():
                pct = (count / self.report["total_rows"]) * 100
                print(f"  ⚠️ Column '{col}': Missing {count} values ({pct:.2f}% of dataset)")
        else:
            print("  ✓ Perfect completeness. No null values detected.")

        # 3. Type Consistency Violations
        print("\n🧬 2. TYPE HOMOGENEITY CHECK:")
        if self.report["type_mismatches"]:
            clean_bill_of_health = False
            for col, info in self.report["type_mismatches"].items():
                print(f"  ⚠️ Column '{col}' contains mixed data types!")
                print(f"     Found classes: {info['detected_types']}")
                print(f"     Distribution:  {info['distribution']}")
        else:
            print("  ✓ Type consistency verified. All columns are structurally homogenous.")

        # 4. Uniqueness Checks
        print("\n🆔 3. UNIQUENESS CHECK:")
        if self.report["duplicate_rows"] > 0:
            clean_bill_of_health = False
            print(f"  ⚠️ Detected {self.report['duplicate_rows']} completely identical duplicate rows.")
        else:
            print("  ✓ Integrity verified. No duplicate records found.")

        # Summary
        print("\n" + "="*50)
        if clean_bill_of_health:
            print("[STATUS] PASSED: Dataset meets structural entry criteria.")
        else:
            print("[STATUS] WARNING: Discrepancies detected. Review required before warehouse load.")
        print("="*50 + "\n")


if __name__ == "__main__":
    # Operational Guardrail: Enforce CLI argument input
    if len(sys.argv) < 2:
        print("Usage Error: Please supply the path to your target dataset.")
        print("Example:    python profile_dataset.py your_data.csv")
        sys.exit(1)

    target_csv = sys.argv[1]
    profiler = DataQualityProfiler(target_csv)
    profiler.execute_profile()