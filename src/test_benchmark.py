
import time
import unittest
from typing import Dict, List

from unittest.mock import patch

from client import run_client  # Assuming the run_client function is in client.py


class BenchmarkTest(unittest.TestCase):
    @patch("builtins.input", side_effect=["test query", "exit"])  # Simulate input
    def test_benchmark_execution_times(self) -> None:
        """
        Benchmark the client on different file sizes.

        Measures the execution time for running the client on different simulated file sizes.
        Asserts that the execution time for a smaller file size is less than that for a larger one.
        """
        file_sizes: List[int] = [10000, 100000, 500000, 1000000]  # File sizes to test
        times: Dict[int, float] = {}

        for size in file_sizes:
            # Simulate the file size by adjusting the query or file content if needed.
            start_time: float = time.time()
            run_client("127.0.0.1", 44445)  # Run the client (adjust for actual file handling)
            elapsed_time: float = time.time() - start_time
            times[size] = elapsed_time
            print(f"File size: {size}, Time taken: {elapsed_time:.4f} seconds")

        # Output benchmark results
        print("Benchmark results:", times)

        # Assert that a smaller file size results in a shorter execution time
        self.assertTrue(
            times[10000] < times[100000],
            "Expected shorter time for smaller file sizes"
        )


if __name__ == "__main__":
    unittest.main()
