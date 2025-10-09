FROM thales884/alpha:1

USER root

# Install system dependencies needed for some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libatlas-base-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

USER $NB_UID

# Copy requirements.txt into the container
COPY Charts/ /app/Charts

# Install Python packages
RUN pip install --upgrade pip 
    


EXPOSE 8888

CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]
