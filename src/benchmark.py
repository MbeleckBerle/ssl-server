import time
import random
import string
import matplotlib.pyplot as plt
from fpdf import FPDF
from typing import List, Dict


# Function to simulate file search algorithms
def naive_search(file_content: List[str], query: str) -> bool:
    """
    A simple naive search for the query in the file content.
    Returns True if the query matches a line exactly, False otherwise.
    """
    for line in file_content:
        if line.strip() == query:
            return True
    return False


def binary_search(file_content: List[str], query: str) -> bool:
    """
    A binary search for the query in the sorted file content.
    Assumes file content is sorted.
    """
    low, high = 0, len(file_content) - 1
    while low <= high:
        mid = (low + high) // 2
        if file_content[mid].strip() == query:
            return True
        elif file_content[mid].strip() < query:
            low = mid + 1
        else:
            high = mid - 1
    return False


def hash_set_search(file_content: List[str], query: str) -> bool:
    """
    A search using a hash set for faster lookups.
    """
    file_set = set(file_content)
    return query in file_set


def regex_search(file_content: List[str], query: str) -> bool:
    """
    A regex-based search for the query.
    """
    import re
    pattern = re.compile(rf"^{re.escape(query)}$")
    return any(pattern.match(line.strip()) for line in file_content)


def optimized_search(file_content: List[str], query: str) -> bool:
    """
    An optimized search using Python's built-in "in" operator.
    """
    return query in file_content


def benchmark_search_algorithm(algorithm, file_content: List[str], query: str) -> float:
    """
    Benchmark the search algorithm and return the time taken to perform the search.
    """
    start_time = time.time()
    algorithm(file_content, query)
    return time.time() - start_time


# Simulate file content (for testing)
def generate_file_content(num_lines: int) -> List[str]:
    """
    Generate a list of lines to simulate a file with `num_lines` entries.
    """
    return [''.join(random.choices(string.ascii_lowercase + string.digits, k=50)) for _ in range(num_lines)]


# Create file content for benchmarking
file_content = generate_file_content(200000)  # File with 200,000 lines

# Algorithms to benchmark
algorithms = {
    'naive_search': naive_search,
    'binary_search': binary_search,
    'hash_set_search': hash_set_search,
    'regex_search': regex_search,
    'optimized_search': optimized_search,
}

# Results dictionary to store execution times for each algorithm
results = {name: [] for name in algorithms}

# Query for testing
query = random.choice(file_content)  # Random query from the file content

# Benchmark each algorithm
for name, algorithm in algorithms.items():
    # Benchmark multiple runs to get a more stable average time
    times = []
    for _ in range(5):  # Running the benchmark 5 times for averaging
        time_taken = benchmark_search_algorithm(algorithm, file_content, query)
        times.append(time_taken)

    # Store the times for this algorithm (not average, just raw data for plotting)
    results[name].extend(times)

    # Print the result for each algorithm
    avg_time = sum(times) / len(times)
    print(f"{name} - Average time: {avg_time:.6f} seconds")

# Plot the results for the graph
plt.figure(figsize=(10, 4))  # Adjusted figure size to fit both graph and table
plt.subplots_adjust(bottom=0.25, top=0.75)  # Adjust margins to fit on one page

# Plot the raw execution times for each algorithm
for name, times in results.items():
    plt.plot(range(1, len(times) + 1), times, label=name)

plt.xlabel('Benchmark Run')
plt.ylabel('Execution Time (seconds)')
plt.title('Benchmarking Search Algorithms')
plt.legend()

# Save the plot to a file (we'll include this in the PDF later)
graph_filename = "benchmark_graph.png"
plt.savefig(graph_filename)

# Now, create a PDF report
pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()

# Add a title
pdf.set_font('Arial', 'B', 16)
pdf.cell(200, 10, 'Benchmarking Search Algorithms', ln=True, align='C')

# Add the graph to the first part of the page
pdf.ln(10)  # Add a line break
pdf.image(graph_filename, x=10, w=180)  # Adjust the position and width of the image

# Space between graph and table
pdf.ln(40)  # Reduce space between the graph and the table to fit on one page

# Add table title
pdf.set_font('Arial', 'B', 16)
pdf.cell(200, 10, 'Performance Table', ln=True, align='C')

# Add table headers
pdf.ln(10)  # Add a line break
pdf.set_font('Arial', 'B', 12)
pdf.cell(100, 10, 'Algorithm', border=1)
pdf.cell(50, 10, 'Average Time (s)', border=1)
pdf.ln()

# Add table rows for each algorithm
pdf.set_font('Arial', '', 12)
for name, times in results.items():
    avg_time = sum(times) / len(times)
    pdf.cell(100, 10, name, border=1)
    pdf.cell(50, 10, f'{avg_time:.6f}', border=1)
    pdf.ln()

# Save the PDF file
pdf_output_filename = "benchmark_report.pdf"
pdf.output(pdf_output_filename)

print(f"Benchmark report saved to {pdf_output_filename}")
