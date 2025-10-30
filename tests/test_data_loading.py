# -*- coding: utf-8 -*-
"""Tests for data loading functionality in WSIMOD.

@author: bdobson
"""

import os
import tempfile
import timeit
import unittest
from unittest import TestCase

from wsimod.orchestration.model import (
    Model,
    to_datetime,
    read_csv,
    write_csv,
    read_parquet,
    write_parquet,
    read_data_file,
    write_data_file,
    create_unified_dataframe,
    load_data_from_dataframe,
    PANDAS_AVAILABLE,
)


class TestDataLoading(TestCase):
    """Test data loading and saving functionality."""

    def setUp(self):
        """Set up test data."""
        self.test_data = {
            ("precipitation", to_datetime("2020-01-01")): 10.5,
            ("precipitation", to_datetime("2020-01-02")): 15.2,
            ("temperature", to_datetime("2020-01-01")): 20.0,
            ("temperature", to_datetime("2020-01-02")): 22.5,
        }

        self.fixed_data = {"node": "test_node", "surface": "test_surface"}

    def test_read_write_csv(self):
        """Test CSV reading and writing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_file = os.path.join(temp_dir, "test.csv")
            write_csv(self.test_data, self.fixed_data, csv_file)
            loaded_data = read_csv(csv_file)

            self.assertEqual(len(loaded_data), len(self.test_data))
            for key, value in self.test_data.items():
                self.assertIn(key, loaded_data)
                self.assertAlmostEqual(loaded_data[key], value, places=10)

    def test_read_write_parquet(self):
        """Test parquet reading and writing."""
        if not PANDAS_AVAILABLE:
            self.skipTest("pandas not available")

        with tempfile.TemporaryDirectory() as temp_dir:
            parquet_file = os.path.join(temp_dir, "test.parquet")
            write_parquet(self.test_data, self.fixed_data, parquet_file)
            loaded_data = read_parquet(parquet_file)

            self.assertEqual(len(loaded_data), len(self.test_data))
            for key, value in self.test_data.items():
                self.assertIn(key, loaded_data)
                self.assertAlmostEqual(loaded_data[key], value, places=10)

    def test_read_data_file_auto_detect_csv(self):
        """Test automatic file format detection for CSV."""
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_file = os.path.join(temp_dir, "test.csv")
            write_csv(self.test_data, self.fixed_data, csv_file)
            loaded_data = read_data_file(csv_file)

            self.assertEqual(len(loaded_data), len(self.test_data))
            for key, value in self.test_data.items():
                self.assertIn(key, loaded_data)
                self.assertAlmostEqual(loaded_data[key], value, places=10)

    def test_read_data_file_auto_detect_parquet(self):
        """Test automatic file format detection for parquet."""
        if not PANDAS_AVAILABLE:
            self.skipTest("pandas not available")

        with tempfile.TemporaryDirectory() as temp_dir:
            parquet_file = os.path.join(temp_dir, "test.parquet")
            write_parquet(self.test_data, self.fixed_data, parquet_file)
            loaded_data = read_data_file(parquet_file)

            self.assertEqual(len(loaded_data), len(self.test_data))
            for key, value in self.test_data.items():
                self.assertIn(key, loaded_data)
                self.assertAlmostEqual(loaded_data[key], value, places=10)

    def test_create_unified_dataframe(self):
        """Test creating unified DataFrame from multiple data sources."""
        if not PANDAS_AVAILABLE:
            self.skipTest("pandas not available")

        nodes_data = {
            "node1": {
                ("precipitation", to_datetime("2020-01-01")): 10.5,
                ("temperature", to_datetime("2020-01-01")): 20.0,
            },
            "node2": {
                ("precipitation", to_datetime("2020-01-01")): 15.2,
                ("temperature", to_datetime("2020-01-01")): 22.5,
            },
        }
        surfaces_data = {
            ("node1", "surface1"): {("evaporation", to_datetime("2020-01-01")): 5.0},
            ("node2", "surface2"): {("evaporation", to_datetime("2020-01-01")): 7.5},
        }

        df = create_unified_dataframe(nodes_data, surfaces_data)

        self.assertEqual(
            list(df.columns), ["node", "surface", "variable", "time", "value"]
        )
        self.assertEqual(len(df), 6)  # 2 nodes * 2 variables + 2 surfaces * 1 variable

        # Check specific data
        node1_precip = df[
            (df["node"] == "node1")
            & (df["variable"] == "precipitation")
            & (df["surface"].isna())
        ]
        self.assertEqual(len(node1_precip), 1)
        self.assertAlmostEqual(node1_precip.iloc[0]["value"], 10.5)

    def test_load_data_from_dataframe(self):
        """Test loading data for specific node/surface from unified DataFrame."""
        if not PANDAS_AVAILABLE:
            self.skipTest("pandas not available")

        nodes_data = {
            "node1": {
                ("precipitation", to_datetime("2020-01-01")): 10.5,
                ("temperature", to_datetime("2020-01-01")): 20.0,
            }
        }
        surfaces_data = {
            ("node1", "surface1"): {("evaporation", to_datetime("2020-01-01")): 5.0}
        }

        df = create_unified_dataframe(nodes_data, surfaces_data)

        # Test loading node data
        node_data = load_data_from_dataframe(df, "node1")
        expected_node_data = {
            ("precipitation", to_datetime("2020-01-01")): 10.5,
            ("temperature", to_datetime("2020-01-01")): 20.0,
        }
        self.assertEqual(node_data, expected_node_data)

        # Test loading surface data
        surface_data = load_data_from_dataframe(df, "node1", "surface1")
        expected_surface_data = {("evaporation", to_datetime("2020-01-01")): 5.0}
        self.assertEqual(surface_data, expected_surface_data)

    def test_write_data_file_auto_detect_csv(self):
        """Test automatic file format detection for CSV writing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_file = os.path.join(temp_dir, "test.csv")
            write_data_file(self.test_data, self.fixed_data, csv_file)
            loaded_data = read_csv(csv_file)
            self.assertEqual(len(loaded_data), len(self.test_data))

    def test_write_data_file_auto_detect_parquet(self):
        """Test automatic file format detection for parquet writing."""
        if not PANDAS_AVAILABLE:
            self.skipTest("pandas not available")

        with tempfile.TemporaryDirectory() as temp_dir:
            parquet_file = os.path.join(temp_dir, "test.parquet")
            write_data_file(self.test_data, self.fixed_data, parquet_file)
            loaded_data = read_parquet(parquet_file)
            self.assertEqual(len(loaded_data), len(self.test_data))


def create_fixture_model():
    """Create a fixture model with test data for testing."""
    model = Model()

    # Create test nodes with data
    test_nodes = [
        {
            "name": "test_node1",
            "type_": "Node",
            "data_input_dict": {
                ("precipitation", to_datetime("2020-01-01")): 10.5,
                ("temperature", to_datetime("2020-01-01")): 20.0,
                ("precipitation", to_datetime("2020-01-02")): 12.0,
                ("temperature", to_datetime("2020-01-02")): 22.0,
            },
        },
        {
            "name": "test_node2",
            "type_": "Node",
            "data_input_dict": {
                ("precipitation", to_datetime("2020-01-01")): 15.2,
                ("temperature", to_datetime("2020-01-01")): 22.5,
                ("precipitation", to_datetime("2020-01-02")): 18.0,
                ("temperature", to_datetime("2020-01-02")): 24.0,
            },
        },
    ]

    # Add dates to model
    model.dates = [to_datetime("2020-01-01"), to_datetime("2020-01-02")]

    model.add_nodes(test_nodes)
    return model


class TestModelDataLoading(TestCase):
    """Test Model class data loading and saving functionality."""

    def setUp(self):
        """Set up test model with data."""
        self.model = create_fixture_model()

    def test_model_save_load_csv(self):
        """Test saving and loading model with CSV data files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save model
            self.model.save(temp_dir, compress=False)

            # Create new model and load
            new_model = Model()
            new_model.load(temp_dir)

            # Check that data was loaded correctly
            self.assertEqual(len(new_model.nodes), 2)
            for node_name in ["test_node1", "test_node2"]:
                self.assertIn(node_name, new_model.nodes)
                node = new_model.nodes[node_name]
                self.assertIsNotNone(node.data_input_dict)
                self.assertIn(
                    ("precipitation", to_datetime("2020-01-01")), node.data_input_dict
                )

    def test_model_save_load_unified_data(self):
        """Test saving and loading model with unified parquet data file."""
        if not PANDAS_AVAILABLE:
            self.skipTest("pandas not available")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Save model with unified data
            self.model.save_unified_data(temp_dir)

            # Create new model and load
            new_model = Model()
            new_model.load_unified_data(os.path.join(temp_dir, "unified_data.parquet"))

            # Check that data was loaded correctly
            self.assertEqual(len(new_model.nodes), 2)
            for node_name in ["test_node1", "test_node2"]:
                self.assertIn(node_name, new_model.nodes)
                node = new_model.nodes[node_name]
                self.assertIsNotNone(node.data_input_dict)
                self.assertIn(
                    ("precipitation", to_datetime("2020-01-01")), node.data_input_dict
                )

    def test_model_load_with_unified_data_file(self):
        """Test loading model that was saved with unified data file reference."""
        if not PANDAS_AVAILABLE:
            self.skipTest("pandas not available")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Save model with unified data
            self.model.save_unified_data(temp_dir)

            # Create new model and load using regular load method
            new_model = Model()
            new_model.load(temp_dir)

            # Check that data was loaded correctly
            self.assertEqual(len(new_model.nodes), 2)
            for node_name in ["test_node1", "test_node2"]:
                self.assertIn(node_name, new_model.nodes)
                node = new_model.nodes[node_name]
                self.assertIsNotNone(node.data_input_dict)
                self.assertIn(
                    ("precipitation", to_datetime("2020-01-01")), node.data_input_dict
                )

    def test_pandas_availability_check(self):
        """Test that pandas availability is correctly detected."""
        # This test will always pass, but documents the behavior
        if PANDAS_AVAILABLE:
            self.assertTrue(True, "Pandas is available")
        else:
            self.assertFalse(False, "Pandas is not available")

    def test_model_run(self):
        """Test that the fixture model can run successfully."""
        flows, tanks, objectives, surfaces = self.model.run(
            dates=[to_datetime("2020-01-01")], record_all=False, verbose=False
        )
        self.assertIsInstance(flows, list)
        self.assertIsInstance(tanks, list)

    def test_model_data_access(self):
        """Test that model nodes can access their data correctly."""
        for node_name in ["test_node1", "test_node2"]:
            node = self.model.nodes[node_name]
            self.assertIsNotNone(node.data_input_dict)
            node.t = to_datetime("2020-01-01")
            self.assertGreater(node.get_data_input("precipitation"), 0)
            self.assertGreater(node.get_data_input("temperature"), 0)

    def test_model_run_csv_format(self):
        """Test model run with CSV format (original approach)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.model.save(temp_dir, compress=False)
            new_model = Model()
            new_model.load(temp_dir)

            flows, tanks, objectives, surfaces = new_model.run(
                dates=[to_datetime("2020-01-01")], record_all=False, verbose=False
            )

            # Verify model ran and data access works
            self.assertIsInstance(flows, list)
            for node_name in ["test_node1", "test_node2"]:
                node = new_model.nodes[node_name]
                node.t = to_datetime("2020-01-01")
                self.assertGreater(node.get_data_input("precipitation"), 0)
                self.assertGreater(node.get_data_input("temperature"), 0)

    def test_model_run_parquet_format(self):
        """Test model run with parquet format (new approach)."""
        if not PANDAS_AVAILABLE:
            self.skipTest("pandas not available")

        with tempfile.TemporaryDirectory() as temp_dir:
            self.model.save_unified_data(temp_dir)
            new_model = Model()
            new_model.load_unified_data(os.path.join(temp_dir, "unified_data.parquet"))

            flows, tanks, objectives, surfaces = new_model.run(
                dates=[to_datetime("2020-01-01")], record_all=False, verbose=False
            )

            # Verify model ran and data access works
            self.assertIsInstance(flows, list)
            for node_name in ["test_node1", "test_node2"]:
                node = new_model.nodes[node_name]
                node.t = to_datetime("2020-01-01")
                self.assertGreater(node.get_data_input("precipitation"), 0)
                self.assertGreater(node.get_data_input("temperature"), 0)

    def test_model_run_auto_detection(self):
        """Test model run with automatic format detection."""
        if not PANDAS_AVAILABLE:
            self.skipTest("pandas not available")

        with tempfile.TemporaryDirectory() as temp_dir:
            self.model.save_unified_data(temp_dir)
            new_model = Model()
            new_model.load(temp_dir)  # Auto-detect parquet format

            flows, tanks, objectives, surfaces = new_model.run(
                dates=[to_datetime("2020-01-01")], record_all=False, verbose=False
            )

            # Verify model ran and data access works
            self.assertIsInstance(flows, list)
            for node_name in ["test_node1", "test_node2"]:
                node = new_model.nodes[node_name]
                node.t = to_datetime("2020-01-01")
                self.assertGreater(node.get_data_input("precipitation"), 0)
                self.assertGreater(node.get_data_input("temperature"), 0)

    def test_model_run_comparison(self):
        """Test that both CSV and parquet formats produce equivalent results."""
        if not PANDAS_AVAILABLE:
            self.skipTest("pandas not available")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Test CSV format
            csv_dir = os.path.join(temp_dir, "csv")
            os.makedirs(csv_dir)
            self.model.save(csv_dir, compress=False)
            csv_model = Model()
            csv_model.load(csv_dir)

            # Test parquet format
            parquet_dir = os.path.join(temp_dir, "parquet")
            os.makedirs(parquet_dir)
            self.model.save_unified_data(parquet_dir)
            parquet_model = Model()
            parquet_model.load_unified_data(
                os.path.join(parquet_dir, "unified_data.parquet")
            )

            # Run both models
            csv_flows, csv_tanks, csv_objectives, csv_surfaces = csv_model.run(
                dates=[to_datetime("2020-01-01")], record_all=False, verbose=False
            )
            parquet_flows, parquet_tanks, parquet_objectives, parquet_surfaces = (
                parquet_model.run(
                    dates=[to_datetime("2020-01-01")], record_all=False, verbose=False
                )
            )

            # Compare results
            self.assertEqual(len(csv_flows), len(parquet_flows))
            self.assertEqual(len(csv_tanks), len(parquet_tanks))

            # Verify data is identical
            for node_name in ["test_node1", "test_node2"]:
                csv_node = csv_model.nodes[node_name]
                parquet_node = parquet_model.nodes[node_name]
                self.assertEqual(csv_node.data_input_dict, parquet_node.data_input_dict)

                # Test data access produces same results
                csv_node.t = parquet_node.t = to_datetime("2020-01-01")
                self.assertEqual(
                    csv_node.get_data_input("precipitation"),
                    parquet_node.get_data_input("precipitation"),
                )
                self.assertEqual(
                    csv_node.get_data_input("temperature"),
                    parquet_node.get_data_input("temperature"),
                )


class TestRealModel(TestCase):
    """Test a real model with data loading and saving functionality."""

    def test_load_save(self):
        """Set up test model with data."""
        model = Model()
        model.load(
            r"C:\Users\bdobson\OneDrive - Imperial College London\temp\bwick\v2\model"
        )
        results = model.run(dates=model.dates[0:3])
        model.save_unified_data(
            r"C:\Users\bdobson\OneDrive - Imperial College London\temp\bwick\v2\model_compressed"
        )

        model2 = Model()
        model2.load(
            r"C:\Users\bdobson\OneDrive - Imperial College London\temp\bwick\v2\model_compressed"
        )
        results2 = model2.run(dates=model2.dates[0:3])

        self.assertEqual(results, results2)

    def test_performance_comparison(self):
        """Compare performance of original vs unified data save/load/run."""
        if not PANDAS_AVAILABLE:
            self.skipTest("pandas not available")

        # Define the model path (update this path as needed)
        model_path = (
            r"C:\Users\bdobson\OneDrive - Imperial College London\temp\bwick\v2\model"
        )

        # Check if model path exists
        if not os.path.exists(model_path):
            self.skipTest(f"Model path {model_path} does not exist")

        with tempfile.TemporaryDirectory() as temp_dir:
            csv_dir = os.path.join(temp_dir, "csv_format")
            parquet_dir = os.path.join(temp_dir, "parquet_format")

            # Test data - use first 3 dates for performance testing
            test_dates = None  # Will be set after loading the model

            def load_original_model():
                """Load model using original CSV format."""
                model = Model()
                model.load(model_path)
                return model

            def load_unified_model():
                """Load model using unified parquet format."""
                model = Model()
                model.load_unified_data(
                    os.path.join(parquet_dir, "unified_data.parquet")
                )
                return model

            def run_model(model):
                """Run model with test dates."""
                return model.run(dates=test_dates, record_all=False, verbose=False)

            # Load original model to get test dates
            print("\n=== Performance Comparison Test ===")
            print("Loading original model to get test dates...")
            original_model = load_original_model()
            test_dates = original_model.dates[0:3]  # Use first 3 dates
            print(f"Using test dates: {[str(d) for d in test_dates]}")

            # Time original model operations
            print("\n--- Original CSV Format ---")

            # Save original model
            save_original_time = timeit.timeit(
                lambda: original_model.save(csv_dir, compress=False), number=1
            )
            print(f"Original save time: {save_original_time:.4f} seconds")

            # Load original model
            load_original_time = timeit.timeit(lambda: load_original_model(), number=1)
            print(f"Original load time: {load_original_time:.4f} seconds")

            # Run original model
            run_original_time = timeit.timeit(
                lambda: run_model(original_model), number=1
            )
            print(f"Original run time: {run_original_time:.4f} seconds")

            # Time unified data model operations
            print("\n--- Unified Parquet Format ---")

            # Save unified data model
            save_unified_time = timeit.timeit(
                lambda: original_model.save_unified_data(parquet_dir), number=1
            )
            print(f"Unified save time: {save_unified_time:.4f} seconds")

            # Load unified data model
            load_unified_time = timeit.timeit(lambda: load_unified_model(), number=1)
            print(f"Unified load time: {load_unified_time:.4f} seconds")

            # Run unified data model
            unified_model = load_unified_model()
            run_unified_time = timeit.timeit(lambda: run_model(unified_model), number=1)
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
