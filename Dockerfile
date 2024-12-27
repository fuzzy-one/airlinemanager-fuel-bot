# Use a lightweight Python image
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the script and environment files
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the Python script
CMD ["python", "main.py"]
