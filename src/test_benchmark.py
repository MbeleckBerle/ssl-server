import time
import unittest
from unittest.mock import patch
from client import run_client  # Assuming the run_client function is in client.py

class BenchmarkTest(unittest.TestCase):

    @patch('builtins.input', side_effect=['test query', 'exit'])  # Simulate input
    def test_benchmark_execution_times(self):
        """Benchmark the client on different file sizes."""
        file_sizes = [10000, 100000, 500000, 1000000]  # File sizes to test
        times = {}

        for size in file_sizes:
            # Simulate the file size by adjusting the query or file content
            start_time = time.time()
            run_client("127.0.0.1", 44445)  # Run the client (adjust for actual file handling)
            elapsed_time = time.time() - start_time
            times[size] = elapsed_time
            print(f"File size: {size}, Time taken: {elapsed_time:.4f} seconds")

        # Save or assert times for further analysis
        print("Benchmark results:", times)
        self.assertTrue(times[10000] < times[100000], "Expected shorter time for smaller file sizes")
