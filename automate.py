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

from asyncio import Task
import csv
import inspect
from itertools import combinations
from logging import config
import logging
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
from PIL import Image, ImageFilter, ImageEnhance
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

def sort_contacts(task: str):
    parts = task.lower().split(" ")
    sort_by = "first_name" if "first" in parts else "last_name"
    order = "desc" if "descending" in parts else "asc"
    
    contacts_file = os.path.join(DATA_DIR, "contacts.json")
    if not os.path.exists(contacts_file):
        return "Contacts file not found."

    with open(contacts_file, "r") as f:
        contacts = json.load(f)

    reverse_order = order == "desc"
    contacts.sort(key=lambda x: x.get(sort_by, "").lower(), reverse=reverse_order)
    
    with open(contacts_file, "w") as f:
        json.dump(contacts, f, indent=4)
    
    return f"Contacts sorted by {sort_by} in {order} order."
def extract_logs(task):
    log_dir = f"{DATA_DIR}/logs"
    
    if not os.path.exists(log_dir):
        raise HTTPException(status_code=404, detail="Log directory not found.")
    
    log_files = [os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.endswith(".log")]

    if not log_files:
        raise HTTPException(status_code=404, detail="No log files found.")

    # Determine sorting order from task description
    task_lower = task.lower()
    if "oldest or old" in task_lower:
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


def clean_and_parse_json(response_text):
    """Cleans and safely parses LLM JSON responses."""
    try:
        # Remove trailing commas before parsing
        cleaned_text = re.sub(r",\s*([\]}])", r"\1", response_text.strip())
        return json.loads(cleaned_text)
    except json.JSONDecodeError:
        logging.error("Invalid JSON response from LLM. Extracting key-value pairs manually.")
        return extract_key_value_pairs_manually(response_text)  # Fallback parsing method


def extract_email_info(task):
    with open(f"{DATA_DIR}/email.txt") as f:
        email_content = f.read()
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Extract sender name, receiver email ID, receiver name, subject, date, and CC from the following email. Return the result strictly as a JSON object with keys: sender_name, receiver_email, receiver_name, subject, date, and cc."},
            {"role": "user", "content": email_content}
        ]
    )

    response_content = response.choices[0].message.content.strip()

    # Debugging: Print response content
    logging.info(f"LLM Response: {response_content}")

    # Remove triple backticks and JSON keyword if present
    response_content = re.sub(r"```json\n(.*?)\n```", r"\1", response_content, flags=re.DOTALL)

    try:
        extracted_info = json.loads(response_content)
    except json.JSONDecodeError:
        logging.error("Invalid JSON response from LLM. Extracting key-value pairs manually.")
        extracted_info = extract_key_value_pairs_manually(response_content)

    # Determine which fields to include based on the query
    requested_fields = []
    field_map = {
        "sender": "sender_name",
        "receiver": "receiver_email",
        "receiver name": "receiver_name",
        "subject": "subject",
        "date": "date",
        "cc": "cc"
    }

    for key in field_map:
        if key in task.lower():
            requested_fields.append(field_map[key])

    if not requested_fields:
        requested_fields = field_map.values()  # Default to all fields if none are explicitly asked

    # Save only the requested fields in a text file
    with open(f"{DATA_DIR}/email-sender.txt", "w") as f:
        for field in requested_fields:
            if field in extracted_info:
                f.write(f"{field.replace('_', ' ').title()}: {extracted_info[field]}\n")

    return {"message": "Email info extracted", "path": f"{DATA_DIR}/email-sender.txt"}

def extract_key_value_pairs_manually(text):
    """Fallback method to extract key-value pairs manually if JSON parsing fails."""
    extracted_data = {}
    matches = re.findall(r'"([\w\s]+)"\s*:\s*"([^"]+)"', text)
    for key, value in matches:
        extracted_data[key] = value
    return extracted_data


def parse_credit_card_info(text: str) -> Dict[str, Optional[str]]:
    card_number_match = re.search(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{1,4}\b", text)
    valid_thru_match = re.search(r"\b(0[1-9]|1[0-2])/\d{2}\b", text)
    cvv_match = re.findall(r"\b\d{3,4}\b", text)

   
    # Exclude words like "VALID" and "THRU" from being detected as names
    name_candidates = re.findall(r"\b[A-Z][A-Z ]{2,}\b", text)
    filtered_names = [name for name in name_candidates if name not in {"VALID", "THRU"}]
    name_match = filtered_names[-1] if filtered_names else None  # Take the last detected name, assuming it appears at the end

    return {
        "credit_card_number": card_number_match.group(0) if card_number_match else None,
        "name": name_match,
        "valid_thru": valid_thru_match if valid_thru_match else None,
        "cvv": cvv_match,
    }
def extract_text_from_image(image_path: str) -> str:
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        print(f"Error processing image: {e}")
        return ""

def extract_credit_card_info(task: str):
    image_path = f"{DATA_DIR}/credit_card.png"
    extracted_text = extract_text_from_image(image_path)
    
    if not extracted_text.strip():
        return {"error": "No text extracted from the image."}
    
    extracted_info = parse_credit_card_info(extracted_text)

    # Determine which fields to include based on the query
    requested_fields = []
    field_map = {
        "card number": "credit_card_number",
        "name": "name",
        "valid thru": "valid_thru",
        "cvv": "cvv"
    }

    for key in field_map:
        if key in task.lower():
            requested_fields.append(field_map[key])

    if not requested_fields:
        requested_fields = field_map.values()  # Default to all fields if none are explicitly asked

    # Save only the requested fields in a text file
    output_file = os.path.join(DATA_DIR, "credit-card.txt")
    try:
        with open(output_file, "w") as f:
            for field in requested_fields:
                if extracted_info[field]:
                    f.write(f"{field}: {extracted_info[field]}\n")
    except Exception as e:
        print(f"Error writing to file: {e}")

    return {field: extracted_info[field] for field in requested_fields}


def find_similar_comments(task: str):
    with open(f"{DATA_DIR}/comments.txt") as f:
        comments = f.readlines()
    response = client.embeddings.create(model="text-embedding-3-small", input=comments)
    embeddings = {comment: emb.embedding for comment, emb in zip(comments, response.data)}
    most_similar = min(embeddings.keys(), key=lambda x: sum(embeddings[x]))
    with open(f"{DATA_DIR}/comments-similar.txt", "w") as f:
        f.writelines(most_similar)
    
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
    Prompt = f"""You are an AI that maps user tasks to predefined function names. 
    Given a task, return the best matching function from this list:

    {", ".join(TASKS.keys())}.

    Ensure the returned function name matches exactly one from the list.
    Respond with only the function name.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": Prompt},
            {"role": "user", "content": task}
        ]
    )
    
    action = response.choices[0].message.content.strip().lower()

    # Debugging LLM output
    print(f"🔍 LLM Response: {action}")

    # Standardizing task name matching
    if "generate data" in action:
        return generate_data()
    elif "count weekday" in action:
        return count_specific_day(task)
    elif "format markdown" in action:
        return format_markdown()
    elif "sort contacts" in action:
        return sort_contacts(task)
    elif ("find" in action or "extract" in action) and ("recent" in action or "old" in action) and "logs" in action:
        return extract_logs(task)
    elif "extract email" in action:
        return extract_email_info(task)
    elif "credit card" in action:
        return extract_credit_card_info(task)
    elif "similar comments" in action:
        return find_similar_comments()
    elif "ticket sales" in action or "total sales" in action:
        return calculate_ticket_sales(task)
    elif "fetch api data" in action:
        return fetch_api_data(task)
    elif "clone git repo" in action or "commit" in action:
        return clone_and_commit_repo(task)
    elif "run sql query" in action:
        return run_sql_query(task)
    elif "scrape website" in action:
        return scrape_website(task)
    elif "resize image" in action or "compress image" in action:
        return compress_resize_image(task)
    elif "transcribe audio" in action:
        return transcribe_audio(task)
    elif "convert markdown" in action:
        return convert_markdown_to_html(task)
    elif "filter csv" in action:
        return filter_csv(task)
    if action in TASKS:
        return TASKS[action](task)
    else:
        raise HTTPException(status_code=400, detail="Task not recognized.")
TASKS = {
    "generate_data": generate_data,
    "count_specific_day": count_specific_day,
    "format_markdown": format_markdown,
    "sort_contacts": sort_contacts,
    "extract_logs": extract_logs,
    "extract_email_info": extract_email_info,
    "extract_credit_card_info": extract_credit_card_info,
    "find_similar_comments": find_similar_comments,
    "calculate_ticket_sales": calculate_ticket_sales,
    "fetch_api_data": fetch_api_data,
    "clone_and_commit_repo": clone_and_commit_repo,
    "run_sql_query": run_sql_query,
    "scrape_website": scrape_website,
    "compress_resize_image": compress_resize_image,
    "transcribe_audio": transcribe_audio,
    "convert_markdown_to_html": convert_markdown_to_html,
    "filter_csv": filter_csv,
    "find_similar_comments": find_similar_comments
}
    

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