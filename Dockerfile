# Use the official Python image from the Docker Hub
FROM python:3.11-slim

# Set environment variables for Poetry
ENV PATH="/root/.local/bin:$PATH"

# Install Poetry
RUN pip install --no-cache-dir poetry

# Set the working directory in the container
WORKDIR /

# Copy the poetry.lock and pyproject.toml files first to leverage Docker cache
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry install --no-root

# Copy the rest of your application code into the container
COPY . .

# Create a shell script to run your application
RUN echo '#!/bin/bash\npoetry run python main.py\nwhile true; do sleep 30; done' > /start.sh && chmod +x /start.sh

# Specify the command to run your application
CMD ["/start.sh"]