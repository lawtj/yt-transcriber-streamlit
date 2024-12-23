# Use an official Python runtime as a parent image
FROM python:3.12-slim

RUN apt-get update

# Set the working directory in the container
WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt

    # Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

    # Copy the current directory contents into the container at /app
COPY . /app


# Make port 8501 available to the world outside this container
EXPOSE 8501

# Run app.py when the container launches
CMD ["streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]