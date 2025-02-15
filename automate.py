
from datetime import datetime
import re
from fastapi import FastAPI, Query, HTTPException,status
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from fastapi.responses import JSONResponse
from subprocess import run
import os
import requests
import shutil
import json
import uvicorn
load_dotenv()
app = FastAPI()
DATA_DIR = "/app/data"  # Ensure this is writable
os.makedirs(DATA_DIR, exist_ok=True)  # Create it if it doesn't exist
response_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "task_runner",
        "schema": {
            "type": "object",
            "required": ["python_dependencies", "python_code"],
            "properties": {
                "python_code": {
                    "type": "string",
                    "description": "Python code to perform the task."
                },
                "python_dependencies": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "module": {"type": "string", "description": "Name of the Python module."},
                        }
                    },
                    "required": ["module"],
                    "additionalProperties": False,
                }
            }
        }    
    }
}

primary_prompt = """
You are an automated agent that generates Python code to complete a given task.
You are an automated Python code generator. Your task is to:
-ensure the datageneration script is saved in current working directory and when it is run results are saved
in the data folder
- Generate a fully functional Python script that performs the requested task.
- Ensure that the script is **syntactically correct** before execution.
- Do not generate any indentation errors, missing imports, or undefined variables.
- If the script needs a directory or file, **create it before using it**.
- The script must be **PEP8-compliant** with correct indentation.
- Before returning the code, **validate it using Python's built-in `compile()` function**.
- If any error occurs during execution, modify the script and retry.
- for the task where a python file is added the the data folder you have to run it with uv run <script>.py <user_email>. this will finish our task completely
## Steps:
1. Generate Python code.
2. **Validate the code** before execution using:
   ```python
   try:
       compile(generated_code, '<string>', 'exec')
   except SyntaxError as e:
       print(f"Syntax Error: {e}")
Follow these steps **strictly**:
- The script must generate a folder in the **current working directory.
- Ensure the folder is **writable** before executing any operations.
- If the folder does not exist, **create it automatically**.
1. **Ensure uv is installed** before running any command. If not, install it.
2. **Always start by downloading and running the script from the given URL**:
   - Fetch `*.py` from the provided URL.
   - Run it using `uv run <script>.py <user_email>` (replace `<user_email>` with the provided email).
   - The script must be executed before any other tasks.
3. all generated files must be saved in the data
4. **Generated Python scripts must be saved with unique filenames**:
   - Example: `llm_code_<timestamp>.py`
5. **Automatically execute the generated script** after writing it.
6. **Log the process**:
   - Redirect `stdout` and `stderr` to `data/output_<timestamp>.log` for debugging.
7. **If a task requires parsing dates, ensure support for multiple formats**:
   - Handle formats like `YYYY-MM-DD`, `DD/MM/YYYY`, `MM-DD-YYYY`, etc.
   - Use `dateutil.parser` for flexible date parsing.
8. **Use `pip3` instead of `pip` for dependencies**.
9. **The final Python script should explicitly write all output files.**
 the output files dshould be given name according to the description in the task.
10. check the generated llm_code for any errors before execution
- **Ensure the output filename is clearly defined inside the generated script**.
- **Before writing any output, the script must determine and use a meaningful filename related to the task**.
- **Example:** If the task is "sort this log file," the script must output `sorted_logs.txt` instead of a generic name.
- **The generated script should print the exact output filename at the end.**

"""
CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

AIPROXY_TOKEN = os.getenv("AIPROXY_TOKEN")
AIPROXY_URL = os.getenv("URL")
headers = {
    "content-type": "application/json",
    "Authorization": f"Bearer {AIPROXY_TOKEN}"
}


def extract_code(response_text):
    """Extract Python code from LLM response."""
    match = re.search(r"```python\n(.*?)```", response_text, re.DOTALL)
    return match.group(1) if match else response_text
def extract_output_filename(python_code):
    """Extracts the output filename from the generated script."""
    match = re.search(r'["\'](/?data/[\w.-]+)["\']', python_code)
    return match.group(1) if match else None

@app.post("/run")
def task_runner(task: str):
    """Determine if task is a script-runner or a task-runner, and execute accordingly."""

    ### **Case 1: Script Runner Task (Download and Run `datagen.py`)**
    if "datagen.py" in task and "https://" in task:
        match = re.search(r"(https?://\S+)\s+with\s+(\S+)", task)
        if not match:
            return {"error": "Invalid script-runner task format. Expected '<URL> with <email>'"}

        script_url, user_email = match.groups()
        script_path = os.path.join(DATA_DIR, "datagen.py")

        # Download script
        response = requests.get(script_url)
        if response.status_code != 200:
            return {"error": "Failed to download script"}

        with open(script_path, "wb") as f:
            f.write(response.content)

        # Execute script (datagen.py itself generates files)
        exec_log_path = os.path.join(DATA_DIR, "execution.log")

        with open(exec_log_path, "w") as log_file:
            process = run(["uv", "run", script_path, user_email], stdout=log_file, stderr=log_file, text=True)

        if process.returncode == 0:
            return {"message": "Script executed successfully", "log_file": exec_log_path}
        else:
            return {"error": "Script execution failed", "log_file": exec_log_path}

    ### **Case 2: LLM-Generated Task (Process the Generated Files)**
    else:
        max_attempts = 3
        attempt = 0
        error_feedback = ""

        while attempt < max_attempts:
            attempt += 1
            print(f"Attempt {attempt}...")

            # LLM Request with error feedback if available
            messages = [
                {"role": "user", "content": task},
                {"role": "system", "content": primary_prompt}
            ]
            if error_feedback:
                messages.append({"role": "user", "content": f"Previous attempt failed:\n{error_feedback}\nFix and retry."})

            response = requests.post("https://aiproxy.sanand.workers.dev/openai/v1/", headers=headers, json={"model": "gpt-4o-mini", "messages": messages})

            if response.status_code != 200:
                return {"error": "Failed to connect to LLM service"}

            try:
                llm_response_text = response.json()['choices'][0]['message']['content']
                python_code = extract_code(llm_response_text)
            except (KeyError, json.JSONDecodeError):
                return {"error": "Invalid LLM response format"}

            # Validate generated Python code
            try:
                compile(python_code, '<string>', 'exec')
            except SyntaxError as e:
                error_feedback = f"Syntax error in generated code: {e}"
                continue

            # Save LLM-generated script
            script_filename = f"llm_task.py"
            script_path = os.path.join(DATA_DIR, script_filename)

            with open(script_path, "w") as f:
                f.write(python_code)

            # Extract output filename from code
            output_filename = extract_output_filename(python_code) or "output.txt"
            output_path = os.path.join(DATA_DIR, output_filename)

            # Execute script and capture output
            with open(output_path, "w") as output_file:
                process = run(["uv", "run", script_path], stdout=output_file, stderr=output_file, text=True)

            if process.returncode == 0:
                return {
                    "script_filename": script_filename,
                    "output_file": output_path,
                    "execution_status": "Success"
                }

            # Capture error for retry
            if os.path.exists(output_path):
                with open(output_path, "r") as output_file:
                    error_feedback = output_file.read()
            else:
                error_feedback = "Execution failed, but no error log was generated."

            # Check if error is due to read-only system
            if "Read-only file system" in error_feedback:
                messages.append({
                    "role": "user",
                    "content": (
                        "Modify the script to write to a writable directory like '/app/data' instead of '/data'."
                    )
                })

            print(f"Execution failed, retrying... (Attempt {attempt})")

        # Return failure after max attempts
        return {
            "script_filename": script_filename,
            "output_file": output_path,
            "execution_status": "Failed after 3 attempts",
            "last_error": error_feedback
        }

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

@app.get("/")
def read_root():
    return {"Hello": "World"}



if __name__ == "__main__":
    uvicorn.run(app,port = 8000)