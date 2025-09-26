import os
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask
import gradio as gr
import logging
import json

from app.processing import pixelate_image_file, pixelate_video_file, pixelate_gif_file
from app.frontend import create_gradio_interface

# Create directories if they don't exist
UPLOADS_DIR = "app/static/uploads"
PROCESSED_DIR = "app/static/processed"
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # This context manager is used to gracefully handle startup and shutdown events.
    # In this case, it helps prevent noisy errors when the server is stopped with Ctrl+C.
    yield
    # Any cleanup code would go here.


app = FastAPI(
    title="Pixel Art Converter API",
    description="An API to pixelate images, videos, and GIFs. Provides a Gradio-based web UI.",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount static files to serve processed images/videos
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.post("/upload/")
async def upload_and_process_file(
    file: UploadFile = File(..., description="The image or video file to be processed."),
    pixel_size: int = Form(16, description="The size of the pixel blocks for pixelation."),
    upscale_factor: int = Form(1, description="The factor by which to upscale the final output.")
):
    if not file.content_type or not file.filename:
        raise HTTPException(status_code=400, detail="Invalid file type")

    # Check for supported file types before proceeding
    if not (file.content_type.startswith('image/') or file.content_type.startswith('video/')):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    file_extension = file.filename.split('.')[-1]
    unique_id = uuid.uuid4()
    input_filename = f"{unique_id}.{file_extension}"
    output_filename = f"{unique_id}_pixelated.{file_extension}"
    input_path = os.path.join(UPLOADS_DIR, input_filename)
    output_path = os.path.join(PROCESSED_DIR, output_filename)

    try:
        # Save uploaded file
        with open(input_path, "wb") as buffer:
            buffer.write(await file.read())

        # Process the file based on its type in a thread pool to avoid blocking
        if file.content_type == 'image/gif':
            await run_in_threadpool(pixelate_gif_file, input_path, output_path, pixel_size, upscale_factor)
        elif file.content_type.startswith('image/'):
            await run_in_threadpool(pixelate_image_file, input_path, output_path, pixel_size, upscale_factor)
        elif file.content_type.startswith('video/'):
            await run_in_threadpool(pixelate_video_file, input_path, output_path, pixel_size, upscale_factor)

        # Return the absolute local path. Gradio will handle serving it.
        return {"processed_file_path": os.path.abspath(output_path)}

    except Exception as e:
        logging.error(f"Error processing file: {file.filename}", exc_info=True)
        # Clean up files in case of an error
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)
        raise HTTPException(status_code=500, detail=f"Error during processing: {e}")
    finally:
        # Optionally, clean up the original uploaded file after processing
        if os.path.exists(input_path):
            os.remove(input_path)

@app.post("/api/pixelate", response_class=FileResponse)
async def pixelate_file_api(
    file: UploadFile = File(..., description="The image or video file to be processed."),
    pixel_size: int = Form(4, description="The size of the pixel blocks for pixelation."),
    upscale_factor: int = Form(1, description="The factor by which to upscale the final output.")
):
    """
    Process a file and return the pixelated version directly as a file response.
    This endpoint is designed for standalone API usage.
    """
    if not file.content_type or not file.filename:
        raise HTTPException(status_code=400, detail="Invalid file type")

    if not (file.content_type.startswith('image/') or file.content_type.startswith('video/')):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    file_extension = file.filename.split('.')[-1]
    unique_id = uuid.uuid4()
    input_filename = f"{unique_id}.{file_extension}"
    output_filename = f"{unique_id}_pixelated.{file_extension}"
    input_path = os.path.join(UPLOADS_DIR, input_filename)
    output_path = os.path.join(PROCESSED_DIR, output_filename)

    try:
        with open(input_path, "wb") as buffer:
            buffer.write(await file.read())

        if file.content_type == 'image/gif':
            await run_in_threadpool(pixelate_gif_file, input_path, output_path, pixel_size, upscale_factor)
        elif file.content_type.startswith('image/'):
            await run_in_threadpool(pixelate_image_file, input_path, output_path, pixel_size, upscale_factor)
        else:
            await run_in_threadpool(pixelate_video_file, input_path, output_path, pixel_size, upscale_factor)

        return FileResponse(
            path=output_path,
            media_type=file.content_type,
            filename=f"pixelated_{file.filename}",
            background=BackgroundTask(os.remove, output_path) # Clean up after sending
        )
    except Exception as e:
        # Ensure cleanup even on failure
        if os.path.exists(output_path):
            os.remove(output_path)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Always clean up the original input file
        if os.path.exists(input_path):
            os.remove(input_path)

@app.get("/manifest.json")
def manifest():
    return json.loads(
        """
        {
            "short_name": "All to Pixelart",
            "name": "Pixelart converter",
            "description": "web application allows you to convert images and videos into a pixel art style. You can upload a file, choose the pixelation level, and apply an upscale factor to the result. The application is built with FastAPI and features a user-friendly interface created with Gradio.",
            "icons": [
                {
                    "src": "static/icon-192x192.png",
                    "type": "image/png",
                    "sizes": "192x192"
                },
                {
                    "src": "static/icon-512x512.png",
                    "type": "image/png",
                    "sizes": "512x512"
                }
            ],
            "start_url": "/",
            "display": "standalone",
            "background_color": "#0b0f19",
            "theme_color": "#4f46e5",
            "orientation": "portrait",
            "scope": "/",
            "lang": "en",
            "categories": ["utilities", "converter", "video"]
        }
        """
    )

# Create and mount Gradio interface
gradio_app = create_gradio_interface()
app = gr.mount_gradio_app(
    app, 
    gradio_app, 
    path="/", 
    allowed_paths=[PROCESSED_DIR]
)
