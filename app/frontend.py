import gradio as gr
import time
import mimetypes
import os
import uuid
import shutil
from .processing import pixelate_image_file, pixelate_video_file, pixelate_gif_file

# Define directories for file storage, ensuring they exist
UPLOADS_DIR = "app/static/uploads"
PROCESSED_DIR = "app/static/processed"
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

def get_file_type(file_path):
    """Determines if a file is an image or a video."""
    if not file_path:
        return None
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        return None
    if mime_type.startswith('image/'):
        return 'image'
    if mime_type.startswith('video/'):
        return 'video'
    return None

def update_previews(file_path):
    """Shows the correct preview component based on the uploaded file type."""
    file_type = get_file_type(file_path)
    is_image = file_type == 'image'
    is_video = file_type == 'video'
    return (
        gr.update(value=file_path if is_image else None, visible=is_image),
        gr.update(value=file_path if is_video else None, visible=is_video),
    )

def upload_and_process(file_path, pixel_size, upscale_factor):
    """
    Handles file processing by calling the appropriate Python function directly.
    This avoids the need for an API call and allows the Gradio app to be shared.
    """
    if file_path is None:
        raise gr.Error("Please upload a file first!")

    # Initial state: clear previous results and show progress
    yield gr.update(value="Processing...", visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)

    input_path = None  # Ensure it's available in the finally block
    try:
        # Generate unique paths for the copied input and the output
        file_extension = os.path.splitext(os.path.basename(file_path))[1]
        unique_id = uuid.uuid4()
        input_filename = f"{unique_id}{file_extension}"
        output_filename = f"{unique_id}_pixelated{file_extension}"
        input_path = os.path.join(UPLOADS_DIR, input_filename)
        output_path = os.path.join(PROCESSED_DIR, output_filename)

        # Copy the uploaded temp file to a persistent location for processing
        shutil.copy(file_path, input_path)

        # Determine file type and process accordingly
        mime_type, _ = mimetypes.guess_type(input_path)
        if mime_type == 'image/gif':
            pixelate_gif_file(input_path, output_path, pixel_size, upscale_factor)
        elif mime_type and mime_type.startswith('image/'):
            pixelate_image_file(input_path, output_path, pixel_size, upscale_factor)
        elif mime_type and mime_type.startswith('video/'):
            pixelate_video_file(input_path, output_path, pixel_size, upscale_factor)
        else:
            raise gr.Error(f"Unsupported file type: {mime_type}. Please upload a valid image or video.")

        time.sleep(1)  # Small delay for better UX

        # Final state: show results
        result_type = get_file_type(output_path)
        is_image = result_type == 'image'
        is_video = result_type == 'video'

        yield (
            gr.update(value="Done!", visible=False),
            gr.update(value=output_path if is_image else None, visible=is_image),
            gr.update(value=output_path if is_video else None, visible=is_video),
            gr.update(value=output_path, visible=True, interactive=True),
        )

    except Exception as e:
        yield gr.update(value=f"Error: {e}", visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)
    finally:
        # Clean up the copied input file
        if input_path and os.path.exists(input_path):
            os.remove(input_path)

def create_gradio_interface():
    """Creates the new Gradio web interface."""
    with gr.Blocks(theme=gr.themes.Soft()) as demo:
        gr.Markdown("## 🖼 Pixel Art Converter")
        gr.Markdown("Upload an image or video, choose the pixelation level, and see the result.")

        # State to hold the uploaded file path
        file_path_state = gr.State(value=None)

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 1. Upload & Configure")
                upload_button = gr.UploadButton("Upload Image or Video", file_types=["image", "video"])
                pixel_size_slider = gr.Slider(minimum=4, maximum=10, value=4, step=1, label="Pixel Size")
                upscale_slider = gr.Slider(minimum=1, maximum=4, value=1, step=1, label="Upscale Factor")
                process_button = gr.Button("Pixelate!", variant="primary")

                gr.Markdown("### Original Preview")
                input_image_preview = gr.Image(label="Original Image", visible=False)
                input_video_preview = gr.Video(label="Original Video", visible=False)

            with gr.Column(scale=2):
                gr.Markdown("### 2. Result")
                status_textbox = gr.Textbox(label="Status", interactive=False, elem_id="status_textbox", visible=False)
                output_image = gr.Image(label="Pixelated Result", visible=False, interactive=False, elem_id="output_image")
                output_video = gr.Video(label="Pixelated Result", visible=False, interactive=False, elem_id="output_video")
                output_downloader = gr.File(label="Download Result", interactive=False, visible=False, elem_id="output_downloader")

        # Link components
        upload_button.upload(
            fn=lambda x: (x, *update_previews(x)),
            inputs=upload_button,
            outputs=[file_path_state, input_image_preview, input_video_preview],
        )

        process_button.click(
            fn=upload_and_process,
            inputs=[file_path_state, pixel_size_slider, upscale_slider],
            outputs=[status_textbox, output_image, output_video, output_downloader],
        )

        return demo

