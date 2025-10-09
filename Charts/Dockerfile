FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy all files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Default entrypoint for dynamic function execution
ENTRYPOINT ["python", "main.py"]
