import gradio as gr
import requests
import time
import mimetypes

API_URL = "http://127.0.0.1:8080/upload/"

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

def upload_and_process(file, pixel_size, upscale_factor):
    """
    Handles file upload, calls the backend, and yields progress updates.
    """
    if file is None:
        raise gr.Error("Please upload a file first!")

    # Initial state: clear previous results and show progress start
    yield gr.update(value="Uploading...", visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)

    try:
        # Step 1: Uploading
        filename = file
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type is None:
            mime_type = 'application/octet-stream'

        with open(filename, 'rb') as f:
            files = {'file': (filename, f, mime_type)}
            data = {'pixel_size': pixel_size, 'upscale_factor': upscale_factor}
            
            response = requests.post(API_URL, files=files, data=data, timeout=600)
            response.raise_for_status()

        # Step 2: Processing
        yield gr.update(value="Pixelating..."), gr.update(), gr.update(), gr.update()
        result = response.json()
        processed_path = result.get("processed_file_path")
        if not processed_path:
            raise gr.Error("Processing failed: No file path returned from server.")
        time.sleep(1) # A small delay to make the progress feel more natural

        # Step 3: Done
        result_type = get_file_type(processed_path)
        is_image = result_type == 'image'
        is_video = result_type == 'video'

        yield (
            gr.update(value="Done!", visible=False),
            gr.update(value=processed_path if is_image else None, visible=is_image),
            gr.update(value=processed_path if is_video else None, visible=is_video),
            gr.update(value=processed_path, visible=True, interactive=True),
        )

    except requests.exceptions.RequestException as e:
        yield gr.update(value=f"Error: {e}", visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)
    except Exception as e:
        yield gr.update(value=f"Error: {e}", visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)

def create_gradio_interface():
    """Creates the new Gradio web interface."""
    with gr.Blocks(theme=gr.themes.Soft()) as demo:
        gr.Markdown("## Pixel Art Converter")
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
