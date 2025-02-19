# search_algorithms.py

import re

def linear_search(file_data, query):
    for line in file_data:
        if query in line:
            return True
    return False

def binary_search(file_data, query):
    file_data.sort()
    low, high = 0, len(file_data) - 1
    while low <= high:
        mid = (low + high) // 2
        if file_data[mid] == query:
            return True
        elif file_data[mid] < query:
            low = mid + 1
        else:
            high = mid - 1
    return False

def hash_search(file_data, query):
    hash_table = {line: True for line in file_data}
    return query in hash_table

def regex_search(file_data, query):
    pattern = re.compile(query)
    for line in file_data:
        if pattern.search(line):
            return True
    return False

def bloom_filter_search(file_data, query):
    size = len(file_data) * 10
    bloom_filter = [False] * size
    def hash_func(word):
        return sum(ord(c) for c in word) % size

    for line in file_data:
        bloom_filter[hash_func(line)] = True

    return bloom_filter[hash_func(query)]
