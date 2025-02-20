import time
import re
from typing import List, Tuple
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


# Sample file-search algorithms
def line_by_line_search(path: str, query: str, reread_on_query: bool) -> int:
    """Search the file line by line."""
    if reread_on_query:
        with open(path, "r", encoding="utf-8") as file:
            return sum(1 for line in file if query in line)
    else:
        lines = read_file_lines(path)
        return sum(1 for line in lines if query in line)


def read_file_lines(path: str) -> List[str]:
    """Read lines of the file into memory."""
    with open(path, "r", encoding="utf-8") as file:
        return file.readlines()


def memory_search(path: str, query: str, reread_on_query: bool) -> int:
    """Search after reading all file lines into memory."""
    if reread_on_query:
        with open(path, "r", encoding="utf-8") as file:
            return sum(1 for line in file if query in line)
    else:
        lines = read_file_lines(path)
        return sum(1 for line in lines if query in line)


def index_search(path: str, query: str, reread_on_query: bool) -> int:
    """Search using an indexed search method (using a dictionary)."""
    if reread_on_query:
        with open(path, "r", encoding="utf-8") as file:
            lines = file.readlines()
    else:
        lines = read_file_lines(path)
    index = {i: line for i, line in enumerate(lines)}
    return sum(1 for line in index.values() if query in line)


def regex_search(path: str, query: str, reread_on_query: bool) -> int:
    """Search using regular expressions."""
    pattern = re.compile(query)
    if reread_on_query:
        with open(path, "r", encoding="utf-8") as file:
            return sum(1 for line in file if pattern.search(line))
    else:
        lines = read_file_lines(path)
        return sum(1 for line in lines if pattern.search(line))


def optimized_search(path: str, query: str, reread_on_query: bool) -> int:
    """Use a more optimized search (e.g., binary search or other methods)."""
    return line_by_line_search(path, query, reread_on_query)


# Function to benchmark algorithms
def benchmark_search_algorithm(algorithm, path: str,
                               query: str, reread_on_query: bool) -> float:
    """Benchmark the performance of a single algorithm."""
    start_time = time.time()
    algorithm(path, query, reread_on_query)
    return (time.time() - start_time) * 1000  # Time in milliseconds


# Function to benchmark all algorithms with both reread options
def benchmark_algorithms(
        path: str, query: str) -> List[Tuple[str, float, float]]:
    """Benchmark multiple algorithms with both reread options."""
    algorithms = [
        ("Line-by-Line", line_by_line_search),
        ("Memory Search", memory_search),
        ("Index Search", index_search),
        ("Regex Search", regex_search),
        ("Optimized Search", optimized_search)
    ]

    results = []
    for name, algo in algorithms:
        reread_time = benchmark_search_algorithm(algo, path,
                                                 query, True)  # Reread
        memory_time = benchmark_search_algorithm(algo, path,
                                                 query, False)  # memory
        time_diff = reread_time - memory_time  # Time difference
        time_ratio = reread_time / memory_time\
            if memory_time != 0 else 0  # Time ratio
        results.append((name, reread_time, memory_time, time_diff, time_ratio))

    # Sort by performance (fastest first for the first reread option)
    results.sort(key=lambda x: x[1])
    return results


# Function to generate speed report as a PDF
def generate_speed_report(path: str, query: str, output_pdf: str):
    """Generate a speed testing report with table and graph."""
    # Benchmark algorithms
    results = benchmark_algorithms(path, query)

    # Prepare the data for the report
    algorithm_names = [result[0] for result in results]
    reread_times = [result[1] for result in results]
    memory_times = [result[2] for result in results]
    time_diffs = [result[3] for result in results]
    time_ratios = [result[4] for result in results]

    # Create a PDF for the report
    c = canvas.Canvas(output_pdf, pagesize=letter)
    c.setFont("Helvetica-Bold", 14)  # Increased font size for title

    # Title centered
    title = "Speed Testing Report"
    title_width = c.stringWidth(title, "Helvetica-Bold", 14)
    c.drawString((letter[0] - title_width) / 2, 780, title)

    # Table header with increased font size and bold
    c.setFont("Helvetica-Bold", 10)  # Bold and increased font size for header
    c.drawString(50, 740, "Algorithm")
    c.drawString(200, 740, "Reread on Query (Time in ms)")
    c.drawString(350, 740, "Read Once (Time in ms)")
    c.drawString(500, 740, "Time Difference (ms)")
    c.drawString(650, 740, "Time Ratio")

    # Add algorithm results to table
    c.setFont("Helvetica", 8)  # Regular font size for table content
    y_position = 720
    for i in range(len(results)):
        c.drawString(50, y_position, algorithm_names[i])
        c.drawString(200, y_position, str(round(reread_times[i], 3)))
        c.drawString(350, y_position, str(round(memory_times[i], 3)))
        c.drawString(500, y_position, str(round(time_diffs[i], 3)))
        c.drawString(650, y_position, str(round(time_ratios[i], 3)))
        y_position -= 18  # Adjusting row height to fit better

    # Create a chart for the results
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(algorithm_names, reread_times,
           width=0.4, label="Reread on Query",
           align='center', color='skyblue')
    ax.bar(algorithm_names, memory_times,
           width=0.4, label="Read Once",
           align='edge', color='lightcoral')

    ax.set_xlabel("Algorithm")
    ax.set_ylabel("Time (ms)")
    ax.set_title("Algorithm Performance Comparison")
    ax.legend()
    plt.tight_layout()

    # Save the chart as an image
    chart_path = "/tmp/speed_test_chart.png"
    plt.savefig(chart_path)
    plt.close()

    # Add chart to the PDF with more space between the table and the chart
    c.drawImage(chart_path, 50, 250, width=500, height=300)

    # Save the PDF
    c.save()

    print(f"Speed testing report saved to {output_pdf}")


# Run the speed test and generate the report
if __name__ == "__main__":

    # Provide the file path and the query string
    generate_speed_report("200k.txt", "search_query", "speed_test_report.pdf")
