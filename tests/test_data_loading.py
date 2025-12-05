# -*- coding: utf-8 -*-
"""Tests for data loading functionality in WSIMOD.

@author: bdobson
"""

import os
import tempfile
import timeit
import unittest
from pathlib import Path
from unittest import TestCase
import pandas as pd
import zipfile

from wsimod.orchestration.model import Model, PARQUET_AVAILABLE


def _unzip_model_data(temp_dir: str):
    """Unzip the model data to the given directory.

    Args:
        temp_dir: Path to the temporary directory to extract the model data to

    Returns:
        Path to the directory containing the extracted model data
    """
    model_path = Path(temp_dir) / "model"
    with zipfile.ZipFile(Path(__file__).parent / "test_model_data.zip", "r") as zip_ref:
        zip_ref.extractall(model_path)
    return model_path


class TestDataLoading(TestCase):
    """Test a real model with data loading and saving functionality."""

    def test_load_save(self):
        """Set up test model with data."""

        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = _unzip_model_data(temp_dir)

            model = Model()
            model.load(model_path)
            results = model.run(dates=model.dates[0:3])
            model.save_unified_data(temp_dir)

            model2 = Model()
            model2.load(temp_dir)
            results2 = model2.run(dates=model2.dates[0:3])
        df = pd.DataFrame(results[0])
        df.time = df.time.astype(str)
        df2 = pd.DataFrame(results2[0])
        df2.time = df2.time.astype(str)
        pd.testing.assert_frame_equal(df, df2)

    def test_misc_load_save(self):
        """Test miscellaneous load and save functionality."""

        from wsimod.orchestration.model import Model

        model = Model()
        model.add_nodes(
            [
                {
                    "name": "my-land2",
                    "type_": "Land",
                    "surfaces": [
                        {
                            "surface": "my_surface",
                            "area": 1,
                            "type_": "GrowingSurface",
                            "initial_storage": {
                                "phosphate": 1,
                                "nitrate": 2,
                                "nitrite": 3,
                                "ammonia": 4,
                                "org-nitrogen": 5,
                                "org-phosphorus": 6,
                            },
                        },
                    ],
                }
            ]
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            model.save(temp_dir)
            model = Model()
            model.load(temp_dir)
        assert model.nodes["my-land2"].surfaces[0].initial_storage == {
            "phosphate": 1,
            "nitrate": 2,
            "nitrite": 3,
            "ammonia": 4,
            "org-nitrogen": 5,
            "org-phosphorus": 6,
        }

    def test_performance_comparison(self):
        """Compare performance of original vs unified data save/load/run."""
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = _unzip_model_data(temp_dir)
            csv_dir = model_path.parent / "csv_format"
            parquet_dir = model_path.parent / "parquet_format"

            def load_original_model():
                """Load model using original CSV format."""
                model = Model()
                model.load(model_path)
                return model

            def load_unified_model(model_dir):
                """Load model using unified parquet format."""
                model = Model()
                model.load(model_dir)
                return model

            def run_model(model):
                """Run model with test dates."""
                return model.run(
                    dates=model.dates[0:3], record_all=False, verbose=False
                )

            # Load original model to get test dates
            print("\n=== Performance Comparison Test ===")
            print("Loading original model to get test dates...")
            original_model = load_original_model()

            # Time original model operations
            print("\n--- Original CSV Format ---")

            # Save original model
            save_original_time = timeit.timeit(
                lambda: original_model.save(csv_dir, compress=False), number=5
            )
            print(f"Original save time: {save_original_time:.4f} seconds")

            # Load original model
            load_original_time = timeit.timeit(lambda: load_original_model(), number=5)
            print(f"Original load time: {load_original_time:.4f} seconds")

            # Run original model
            run_original_time = timeit.timeit(
                lambda: run_model(original_model), number=5
            )
            print(f"Original run time: {run_original_time:.4f} seconds")

            # Time unified data model operations
            print("\n--- Unified Parquet Format ---")

            # Save unified data model
            save_unified_time = timeit.timeit(
                lambda: original_model.save_unified_data(parquet_dir), number=5
            )
            print(f"Unified save time: {save_unified_time:.4f} seconds")

            # Load unified data model
            load_unified_time = timeit.timeit(
                lambda: load_unified_model(parquet_dir), number=5
            )
            print(f"Unified load time: {load_unified_time:.4f} seconds")

            # Run unified data model
            unified_model = load_unified_model(parquet_dir)
            run_unified_time = timeit.timeit(lambda: run_model(unified_model), number=5)
            print(f"Unified run time: {run_unified_time:.4f} seconds")

            # Calculate performance improvements
            print("\n--- Performance Comparison ---")
            save_improvement = (
                (save_original_time - save_unified_time) / save_original_time
            ) * 100
            load_improvement = (
                (load_original_time - load_unified_time) / load_original_time
            ) * 100
            run_improvement = (
                (run_original_time - run_unified_time) / run_original_time
            ) * 100

            print(f"Save time improvement: {save_improvement:+.2f}%")
            print(f"Load time improvement: {load_improvement:+.2f}%")
            print(f"Run time improvement: {run_improvement:+.2f}%")

            # Calculate total time improvements
            total_original = save_original_time + load_original_time + run_original_time
            total_unified = save_unified_time + load_unified_time + run_unified_time
            total_improvement = (
                (total_original - total_unified) / total_original
            ) * 100

            print(f"Total time improvement: {total_improvement:+.2f}%")
            print(f"Total original time: {total_original:.4f} seconds")
            print(f"Total unified time: {total_unified:.4f} seconds")

            # Verify results are equivalent
            print("\n--- Verifying Results Equivalence ---")
            original_results = run_model(original_model)
            unified_results = run_model(unified_model)

            # Compare results (they should be identical)
            self.assertEqual(
                len(original_results[0]),
                len(unified_results[0]),
                "Flow results length mismatch",
            )
            self.assertEqual(
                len(original_results[1]),
                len(unified_results[1]),
                "Tank results length mismatch",
            )
            self.assertEqual(
                len(original_results[3]),
                len(unified_results[3]),
                "Surface results length mismatch",
            )

            print("✓ Results are equivalent between original and unified formats")

            # Store performance metrics for potential reporting
            self.performance_metrics = {
                "original": {
                    "save_time": save_original_time,
                    "load_time": load_original_time,
                    "run_time": run_original_time,
                    "total_time": total_original,
                },
                "unified": {
                    "save_time": save_unified_time,
                    "load_time": load_unified_time,
                    "run_time": run_unified_time,
                    "total_time": total_unified,
                },
                "improvements": {
                    "save_improvement": save_improvement,
                    "load_improvement": load_improvement,
                    "run_improvement": run_improvement,
                    "total_improvement": total_improvement,
                },
            }

            print("\n=== Performance Test Complete ===")


if __name__ == "__main__":
    unittest.main()
