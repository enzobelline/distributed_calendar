# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Set the working directory in the container
WORKDIR /test

# Copy the current directory contents into the container at /app
COPY . /test

# Install Flask and any other dependencies
RUN pip install --no-cache-dir flask

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Define environment variable
ENV NAME World

# Run app.py when the container launches
CMD ["python", "test.py"]
