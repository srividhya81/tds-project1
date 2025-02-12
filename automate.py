# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "uv", 
#   "openai", 
#   "sqlite3", 
#   "requests", 
#   "npx",
#   "fastapi",
#   "python-dotenv",
#   "uvicorn",
#   "Pillow",
#   "pytesseract",
#   "markdown",
#   "pandas",
#   "duckdb",
#   "gitpython",
#   "fastapi.middleware.cors",
#   "bs4",
#   "dateutil",
#   "python-dotenv",
#   "faker"

# ]
# ///   

import csv
import inspect
from logging import config
import shutil
import pytesseract
from fastapi import FastAPI, HTTPException, Query
from typing import Dict, Any, Optional
import subprocess
import json
import sqlite3
import os
import re
import datetime
import sys
from collections import defaultdict
from openai import OpenAI
import requests
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import git
import duckdb
import markdown
import pandas as pd
from dateutil import parser
from PIL import Image
from bs4 import BeautifulSoup

load_dotenv()


app = FastAPI()
client = OpenAI(
    base_url=os.getenv("OPENAI_BASE_URL"),
    api_key=os.getenv("OPENAI_API_KEY")
)

CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

DATA_DIR = "/Users/tds-project1/data"  # Ensure this is writable
os.makedirs(DATA_DIR, exist_ok=True)  # Create it if it doesn't exist

def generate_data():
    email = os.getenv("user_email", "test@example.com")
    url = "https://raw.githubusercontent.com/sanand0/tools-in-data-science-public/tds-2025-01/project-1/datagen.py"
    script_path = os.path.join(DATA_DIR, "datagen.py")

    try:
        response = requests.get(url)
        response.raise_for_status()
        
        with open(script_path, "w") as f:
            f.write(response.text)
        
        with open(script_path, "r") as f:
            script_content = f.read()
        
        script_content = script_content.replace('/data', DATA_DIR)
        
        with open(script_path, "w") as f:
            f.write(script_content)
        
        os.chmod(script_path, 0o755)
        
        subprocess.run(["python3", script_path, email], check=True)
        return "Data generated successfully."
    except requests.exceptions.RequestException as e:
        return f"Failed to download the script: {e}"
    except subprocess.CalledProcessError as e:
        return f"Error executing the script: {e}"



def count_specific_day(task):
    day_map = {
        "sunday": 6, "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5,
        "ravivar": 6, "somvar": 0, "mangalvar": 1, "budhvar": 2, "guruvar": 3, "shukravar": 4, "shanivar": 5,
        "ஞாயிறு": 6, "திங்கள்": 0, "செவ்வாய்": 1, "புதன்": 2, "வியாழன்": 3, "வெள்ளி": 4, "சனி": 5,
        "dimanche": 6, "lundi": 0, "mardi": 1, "mercredi": 2, "jeudi": 3, "vendredi": 4, "samedi": 5,
        "domingo": 6, "lunes": 0, "martes": 1, "miércoles": 2, "jueves": 3, "viernes": 4, "sábado": 5
    }

    target_weekday = None
    for key in day_map:
        if key in task.lower():
            target_weekday = day_map[key]
            break
    if target_weekday is None:
        raise HTTPException(status_code=400, detail="Day not recognized.")

    count = 0
    with open(f"{DATA_DIR}/dates.txt", "r") as f:
        for line in f:
            try:
                date_obj = parser.parse(line.strip(), fuzzy=True)
                if date_obj.weekday() == target_weekday:
                    count += 1
            except ValueError:
                continue  # Skip lines that are not valid dates

    with open(f"{DATA_DIR}/dates-count.txt", "w") as f:
        f.write(str(count))

    return f"Count of {key.capitalize()} calculated successfully."
def format_markdown():
    try:
        subprocess.run(["npx", "prettier@3.4.2", "--write", f"{DATA_DIR}/format.md"], check=True)
        return "Markdown file formatted successfully."
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Error formatting Markdown: {str(e)}")            

def sort_contacts(task):
    # Default sorting order
    sort_keys = [("last_name", "asc"), ("first_name", "asc")]

    # Extract sorting criteria from the task description
    task_lower = task.lower()
    
    # Detect sorting order (ascending or descending)
    if "descending" in task_lower or "desc" in task_lower:
        order = "desc"
    else:
        order = "asc"  # Default

    # Detect which keys to sort by
    if "first name then last name" in task_lower:
        sort_keys = [("first_name", order), ("last_name", order)]
    elif "last name then first name" in task_lower:
        sort_keys = [("last_name", order), ("first_name", order)]
    elif "first name" in task_lower:
        sort_keys = [("first_name", order)]
    elif "last name" in task_lower:
        sort_keys = [("last_name", order)]

    try:
        # Read the contacts file
        with open(f"{DATA_DIR}/contacts.json", "r") as f:
            contacts = json.load(f)

        # Perform sorting based on extracted criteria
        for key, direction in reversed(sort_keys):  # Sort in reverse order for stability
            reverse = direction == "desc"
            contacts.sort(key=lambda x: x.get(key, "").lower(), reverse=reverse)

        # Write the sorted contacts to a new file
        with open(f"{DATA_DIR}/contacts-sorted.json", "w") as f:
            json.dump(contacts, f, indent=2)

        return f"Contacts sorted by {', '.join([f'{k} ({d})' for k, d in sort_keys])} successfully."

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sorting contacts: {str(e)}")
def extract_logs(task):
    log_dir = f"{DATA_DIR}/logs"
    
    if not os.path.exists(log_dir):
        raise HTTPException(status_code=404, detail="Log directory not found.")
    
    log_files = [os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.endswith(".log")]

    if not log_files:
        raise HTTPException(status_code=404, detail="No log files found.")

    # Determine sorting order from task description
    task_lower = task.lower()
    if "oldest" in task_lower:
        log_files.sort(key=os.path.getmtime)  # Sort by oldest first
    else:
        log_files.sort(key=os.path.getmtime, reverse=True)  # Default: most recent first

    # Select the first 10 files
    selected_logs = log_files[:10]

    try:
        with open(f"{DATA_DIR}/logs-recent.txt", "w") as output_file:
            for log in selected_logs:
                with open(log, "r") as log_file:
                    first_line = log_file.readline().strip()
                    output_file.write(first_line + "\n")
        
        return f"Extracted first lines of {'most recent' if 'oldest' not in task_lower else 'oldest'} 10 log files."

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting logs: {str(e)}")
def create_markdown_index():
    docs_dir = f"{DATA_DIR}/docs"
    index = {}

    if not os.path.exists(docs_dir):
        raise HTTPException(status_code=404, detail="Docs directory not found.")

    for root, _, files in os.walk(docs_dir):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        match = re.match(r"^#\s+(.*)", line.strip())
                        if match:
                            relative_path = os.path.relpath(file_path, docs_dir)
                            index[relative_path] = match.group(1)
                            break  # Stop at the first H1

    index_path = os.path.join(docs_dir, "index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)

    return f"Markdown index created at {index_path}"
def extract_email_info(task):
    email_file = f"{DATA_DIR}/email.txt"

    if not os.path.exists(email_file):
        raise HTTPException(status_code=404, detail="Email file not found.")

    with open(email_file, "r", encoding="utf-8") as f:
        email_content = f.read()

    # Define possible extraction requests
    extraction_options = {
        "sender's email": "Extract only the sender's email address.",
        "sender's name": "Extract only the sender's name.",
        "receiver's email": "Extract only the receiver's email address.",
        "receiver's name": "Extract only the receiver's name.",
        "cc emails": "Extract all CC email addresses.",
        "email date": "Extract the date when the email was sent."
    }

    # Determine the specific information to extract
    task_lower = task.lower()
    extract_instruction = "Extract the sender's email address."  # Default task
    for key, instruction in extraction_options.items():
        if key in task_lower:
            extract_instruction = instruction
            break

    # Call LLM to extract the requested detail
    response = client.chat.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": extract_instruction},
            {"role": "user", "content": email_content}
        ]
    )

    extracted_info = response["choices"][0]["message"]["content"].strip()

    # Determine output file dynamically
    file_map = {
        "sender's email": "email-sender.txt",
        "sender's name": "email-sender-name.txt",
        "receiver's email": "email-receiver.txt",
        "receiver's name": "email-receiver-name.txt",
        "cc emails": "email-cc.txt",
        "email date": "email-date.txt"
    }

    output_filename = file_map.get(task_lower, "email-sender.txt")
    output_path = os.path.join(DATA_DIR, output_filename)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(extracted_info)

    return f"Extracted '{task_lower}' and saved to {output_path}"

def extract_credit_card_info(task):
    img_path = f"{DATA_DIR}/credit-card.png"

    if not os.path.exists(img_path):
        raise HTTPException(status_code=404, detail="Credit card image not found.")

    img = Image.open(img_path)
    extracted_text = pytesseract.image_to_string(img)

    # Clean extracted text
    extracted_text = extracted_text.replace("\n", " ").strip()

    # Patterns for extracting information
    patterns = {
        "card number": r"\b(\d{4}[-\s]?\d{4}[-\s]?\d{4})\b",  # 12-digit card number (4-4-4)
        "cvv": r"\b(\d{3})\b",  # 3-digit CVV
        "name": r"([A-Z ]+)\b(?!.*(valid|thru|exp|expiry|cvv))",  # Name without "valid thru"
        "date": r"\b(\d{2}/\d{2})\b"  # MM/YY format
    }

    # Determine what to extract
    task_lower = task.lower()
    extracted_info = None
    for key, pattern in patterns.items():
        if key in task_lower:
            match = re.search(pattern, extracted_text)
            if match:
                extracted_info = match.group(1)
                break

    if not extracted_info:
        raise HTTPException(status_code=400, detail="Requested card information not found.")

    output_filename = f"credit-card-{key.replace(' ', '-')}.txt"
    output_path = os.path.join(DATA_DIR, output_filename)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(extracted_info)

    return f"Extracted '{key}' and saved to {output_path}"
from itertools import combinations

def find_similar_comments():
    comments_file = f"{DATA_DIR}/comments.txt"

    if not os.path.exists(comments_file):
        raise HTTPException(status_code=404, detail="Comments file not found.")

    with open(comments_file, "r", encoding="utf-8") as f:
        comments = [line.strip() for line in f if line.strip()]

    if len(comments) < 2:
        raise HTTPException(status_code=400, detail="Not enough comments to compare.")

    # Generate embeddings
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=comments
    )
    
    embeddings = [entry["embedding"] for entry in response["data"]]

    # Compute cosine similarity
    def cosine_similarity(vec1, vec2):
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude = (sum(a ** 2 for a in vec1) ** 0.5) * (sum(b ** 2 for b in vec2) ** 0.5)
        return dot_product / magnitude if magnitude else 0

    most_similar_pair = None
    highest_similarity = -1

    for (i, j) in combinations(range(len(comments)), 2):
        similarity = cosine_similarity(embeddings[i], embeddings[j])
        if similarity > highest_similarity:
            highest_similarity = similarity
            most_similar_pair = (comments[i], comments[j])

    if not most_similar_pair:
        raise HTTPException(status_code=400, detail="Could not determine the most similar comments.")

    output_path = f"{DATA_DIR}/comments-similar.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(most_similar_pair))

    return f"Most similar comments written to {output_path}"
def calculate_ticket_sales(task):
    db_path = f"{DATA_DIR}/ticket-sales.db"

    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Ticket sales database not found.")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    ticket_types = ["Gold", "Silver", "Bronze"]
    sales_results = {}

    task_lower = task.lower()
    total_sales = 0

    for ticket_type in ticket_types:
        if ticket_type.lower() in task_lower or "total sales" in task_lower:
            cursor.execute("SELECT SUM(units * price) FROM tickets WHERE type=?", (ticket_type,))
            sales_results[ticket_type] = cursor.fetchone()[0] or 0
            total_sales += sales_results[ticket_type]

    conn.close()

    # Determine output file based on task
    if "total sales" in task_lower or "all" in task_lower:
        output_path = f"{DATA_DIR}/ticket-sales-total.txt"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(str(total_sales))
        return f"Total sales of all ticket types written to {output_path}"

    for ticket_type, sales in sales_results.items():
        output_path = f"{DATA_DIR}/ticket-sales-{ticket_type.lower()}.txt"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(str(sales))

    return "Ticket sales calculated successfully."

def fetch_api_data(task):
    url = extract_url_from_task(task)
    if not url:
        raise ValueError("No valid API URL found in the task description.")

    response = requests.get(url)
    response.raise_for_status()

    with open(f"{DATA_DIR}/api-data.json", "w") as f:
        f.write(response.text)

    return f"Data fetched from {url} and saved to api-data.json."

def extract_url_from_task(task):
    words = task.split()
    for word in words:
        if word.startswith("http"):
            return word
    return None
def clone_and_commit_repo(task):
    repo_url = extract_url_from_task(task)
    if not repo_url:
        raise ValueError("No valid Git repository URL found.")

    repo_dir = f"{DATA_DIR}/repo"
    subprocess.run(["git", "clone", repo_url, repo_dir], check=True)

    # Make a commit
    with open(f"{repo_dir}/update.txt", "w") as f:
        f.write("Automated update.")

    subprocess.run(["git", "-C", repo_dir, "add", "."], check=True)
    subprocess.run(["git", "-C", repo_dir, "commit", "-m", "Automated commit"], check=True)
    subprocess.run(["git", "-C", repo_dir, "push"], check=True)

    return f"Cloned and committed to {repo_url}."
def run_sql_query(task):
    query = extract_sql_query_from_task(task)
    if not query:
        raise ValueError("No valid SQL query found.")

    db_path = f"{DATA_DIR}/database.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(query)
    result = cursor.fetchall()
    conn.close()

    with open(f"{DATA_DIR}/sql-result.json", "w") as f:
        json.dump(result, f)

    return "SQL query executed successfully."

def extract_sql_query_from_task(task):
    return task.split(":", 1)[-1].strip() if ":" in task else None
def scrape_website(task):
    url = extract_url_from_task(task)
    if not url:
        raise ValueError("No valid URL found in the task.")

    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text()

    with open(f"{DATA_DIR}/scraped-text.txt", "w") as f:
        f.write(text)

    return "Website data scraped successfully."

def compress_resize_image(task):
    img_path = f"{DATA_DIR}/image.png"
    output_path = f"{DATA_DIR}/image-resized.png"
    size = (500, 500)  # Default size

    img = Image.open(img_path)
    img = img.resize(size)
    img.save(output_path, "PNG")

    return "Image resized successfully."
def transcribe_audio():
    audio_path = f"{DATA_DIR}/audio.mp3"
    
    with open(audio_path, "rb") as f:
        response = client.Audio.transcribe("whisper-1", f)
    
    transcript = response["text"]
    with open(f"{DATA_DIR}/audio-transcription.txt", "w") as f:
        f.write(transcript)

    return "Audio transcription completed."
def convert_markdown_to_html():
    md_path = f"{DATA_DIR}/document.md"
    html_path = f"{DATA_DIR}/document.html"

    with open(md_path, "r") as f:
        md_content = f.read()

    html_content = markdown.markdown(md_content)

    with open(html_path, "w") as f:
        f.write(html_content)

    return "Markdown converted to HTML."
def filter_csv(task):
    csv_path = f"{DATA_DIR}/data.csv"
    output_path = f"{DATA_DIR}/filtered-data.json"

    filter_column, filter_value = extract_filter_from_task(task)
    if not filter_column or not filter_value:
        raise ValueError("No valid filter found.")

    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        filtered_data = [row for row in reader if row.get(filter_column) == filter_value]

    with open(output_path, "w") as f:
        json.dump(filtered_data, f)

    return "Filtered CSV data saved to JSON."

def extract_filter_from_task(task):
    words = task.split()
    if "where" in words:
        index = words.index("where")
        column_value = words[index + 1:]
        return column_value[0], column_value[-1] if len(column_value) > 1 else None
    return None, None
def execute_task(task: str):
    Prompt = """You are an AI that maps user tasks to predefined function names. 
    Given a task, return the best matching function from this list: 

    - generate_data: Install dependencies and run data generation
    - format_file: Format a file using a specified formatter
    - count_weekday: Count occurrences of a specific weekday in a file
    - sort_contacts: Sort contacts by first and last name in ascending or descending order
    - extract_logs: Extract logs based on a given time range (recent, old, or specific period),recent can also be new old can also be past like relatable words should be considered
    - generate_markdown_index: Create an index from Markdown files
    - extract_email_sender: Extract the sender's email from an email file
    - extract_credit_card_info: Extract a credit card number, name, valid thru and cvv number from an image
    - find_similar_comments: Identify the most similar comments using embeddings
    - calculate_ticket_sales: Compute total ticket sales, optionally filtered by ticket type. the ticket type may be specified in query itself like gold ticket sale or silver ticket sales consider that also
    - fetch_api_data: Fetch data from an API and save it to a file
    - clone_git_repo: Clone a Git repository into a folder
    - run_sql_query: Execute an SQL query on a database
    - compress_image: Compress an image file
    - transcribe_audio: Transcribe an audio file
    - convert_markdown_to_html: Convert Markdown content to HTML
    - filter_csv: Filter a CSV file based on a column value


    Respond with only the function name, without extra explanations.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": Prompt},
            {"role": "user", "content": task}
        ]
    )
    action = response.choices[0].message.content.strip().lower()
     # Debugging: Print the LLM response to see if it's correct
    print(f"🔍 LLM Response: {action}")

    # Standardize common variations
    if "generate" in action and "data" in action:
        return generate_data()
    elif "count" in action and "day" in action:
        return count_specific_day(task)
    elif "sort" in action and "contact" in action:
        return sort_contacts()
    elif "find recent logs" in action or "oldest logs" in action:
        return extract_logs(task)
    elif "extract email" in action:
        return extract_email_info(task)
    elif "credit card" in action:
        return extract_credit_card_info(task)
    elif "ticket sales" in action or "total sales" in action:
        return calculate_ticket_sales(task)
    elif "fetch api data" in task.lower():
        return fetch_api_data(task)
    elif "clone repo" in task.lower() or "commit" in task.lower():
        return clone_and_commit_repo(task)
    elif "run sql query" in task.lower():
        return run_sql_query(task)
    elif "scrape website" in task.lower():
        return scrape_website(task)
    elif "resize image" in task.lower() or "compress image" in task.lower():
        return compress_resize_image(task)
    elif "transcribe audio" in task.lower():
        return transcribe_audio()
    elif "convert markdown" in task.lower():
        return convert_markdown_to_html()
    elif "filter csv" in task.lower():
        return filter_csv(task)

    else:
        raise HTTPException(status_code=400, detail="Task not recognized.")
# API Routes
@app.post("/run")
def run_task(task: str = Query(..., description="Task description")):
    try:
        result = execute_task(task)
        return {"message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/read")
def read_file(path: str = Query(..., description="Path to the file")):
    if not path.startswith("/data/"):
        raise HTTPException(status_code=403, detail="Access denied.")
    try:
        with open(path, "r") as f:
            content = f.read()
        return {"content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found.")




# Block deletion functions to prevent accidental deletions
def restricted_os_remove(path):
    raise PermissionError("File deletion is not allowed.")

def restricted_shutil_rmtree(path):
    raise PermissionError("Directory deletion is not allowed.")

os.remove = restricted_os_remove
shutil.rmtree = restricted_shutil_rmtree


if __name__ == "__main__":
    uvicorn.run(app,port = 8040)