import time
import mmap
import re
from typing import List, Tuple


def line_by_line_search(path: str, query: str) -> str:
    """
    Search for a string by reading the file line-by-line.

    :param path: Path to the file to be searched.
    :param query: The string to search for.
    :return: "STRING EXISTS" if found, "STRING NOT FOUND" otherwise.
    """
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            if line.strip() == query:
                return "STRING EXISTS"
    return "STRING NOT FOUND"


def binary_search(path: str, query: str) -> str:
    """
    Perform binary search on a sorted file to find a string.

    :param path: Path to the file to be searched.
    :param query: The string to search for.
    :return: "STRING EXISTS" if found, "STRING NOT FOUND" otherwise.
    """
    with open(path, "r", encoding="utf-8") as file:
        lines = file.readlines()

    lines.sort()
    low, high = 0, len(lines) - 1

    while low <= high:
        mid = (low + high) // 2
        if lines[mid].strip() == query:
            return "STRING EXISTS"
        elif lines[mid].strip() < query:
            low = mid + 1
        else:
            high = mid - 1

    return "STRING NOT FOUND"


def hash_table_search(path: str, query: str) -> str:
    """
    Search for a string using a hash table for faster lookup.

    :param path: Path to the file to be searched.
    :param query: The string to search for.
    :return: "STRING EXISTS" if found, "STRING NOT FOUND" otherwise.
    """
    with open(path, "r", encoding="utf-8") as file:
        lines = file.readlines()

    hash_table = {line.strip(): True for line in lines}
    return "STRING EXISTS" if query in hash_table else "STRING NOT FOUND"


def regex_search(path: str, query: str) -> str:
    """
    Search for a string using regular expressions.

    :param path: Path to the file to be searched.
    :param query: The string to search for.
    :return: "STRING EXISTS" if found, "STRING NOT FOUND" otherwise.
    """
    with open(path, "r", encoding="utf-8") as file:
        content = file.read()

    if re.search(query, content):
        return "STRING EXISTS"

    return "STRING NOT FOUND"


def mmap_search(path: str, query: str) -> str:
    """
    Search for a string using memory-mapped files for fast access.

    :param path: Path to the file to be searched.
    :param query: The string to search for.
    :return: "STRING EXISTS" if found, "STRING NOT FOUND" otherwise.
    """
    with open(path, "r", encoding="utf-8") as file:
        mmapped_file = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)

        if mmapped_file.find(query.encode()) != -1:
            return "STRING EXISTS"

    return "STRING NOT FOUND"


def benchmark_algorithms(path: str, query: str) -> List[Tuple[str, float]]:
    """
    Benchmark various string search algorithms
    and return their execution times.

    :param path: Path to the file to be searched.
    :param query: The string to search for.
    :return: A list of tuples where each tuple
    contains the algorithm name and its execution
    time in milliseconds.
    """
    algorithms = [
        ("Line-by-Line", line_by_line_search),
        ("Binary Search", binary_search),
        ("Hash Table", hash_table_search),
        ("Regex Search", regex_search),
        ("Memory-mapped", mmap_search),
    ]

    results: List[Tuple[str, float]] = []

    for name, algorithm in algorithms:
        start_time = time.time()
        algorithm(path, query)
        end_time = time.time()

        execution_time = (
            end_time - start_time) * 1000  # Convert to milliseconds
        results.append((name, execution_time))

    return results
