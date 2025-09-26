# 1. Use an official Python runtime as a parent image
FROM python:3.10-slim

# 2. Set the working directory in the container
WORKDIR /code

# 3. Copy the dependencies file to the working directory
COPY requirements.txt .

# 4. Install any needed packages specified in requirements.txt
# We use --no-cache-dir to reduce image size
# We also install ffmpeg and other multimedia libraries needed by OpenCV for video processing
RUN apt-get update && apt-get install -y ffmpeg libsm6 libxext6  && \
    pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of the application code
COPY . .

# 6. Allow Gradio to access the static files directory.
# This is a security measure to prevent Server-Side Request Forgery (SSRF).
# The path must be absolute inside the container.
ENV GRADIO_ALLOWED_PATHS="/code/app/static"

# 7. Make port 8000 available to the world outside this container
EXPOSE 8000

# 8. Run app.main when the container launches
# Use --host 0.0.0.0 to make it accessible from outside the container
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
