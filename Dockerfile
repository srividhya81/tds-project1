# Use an official Python image
FROM python:3.10

# Set the working directory
WORKDIR /app

# Copy files into the container
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the FastAPI port
EXPOSE 8000

# Run FastAPI app
CMD ["uvicorn", "automate:app", "--host", "0.0.0.0", "--port", "8000"]

RUN pip install --no-cache-dir uv

# Create writable data directory
RUN mkdir -p /app/data

# Set permissions to allow writing
RUN chmod -R 777 /app/data
