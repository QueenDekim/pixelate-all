# Pixel Art Converter

This web application allows you to convert images, videos, and GIFs into a pixel art style. You can upload a file, choose the pixelation level, and apply an upscale factor to the result. The application is built with FastAPI and features a user-friendly interface created with Gradio.

## Features

- **Image & Video Support**: Pixelate both static images and animated videos.
- **Configurable Pixel Size**: Adjust the level of detail by changing the pixel block size.
- **Upscale Factor**: Increase the resolution of the final output (e.g., 2x, 4x).
- **Web Interface**: Easy-to-use UI powered by Gradio.
- **API Documentation**: Interactive API documentation available via Swagger UI.

## Getting Started

You can run this project either directly with Python or using Docker.

### Prerequisites

- Python 3.9+
- Pip package manager
- Docker (for Docker-based setup)

### Option 1: Running with Python

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/QueenDekim/pixelate-all.git
    cd pixelate-all
    ```

2.  **Create and activate a virtual environment** (recommended):
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    # On Windows, use: .venv\Scripts\activate
    ```

3.  **Install the dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the application**:

    The application is now run as a module to support command-line arguments.

    ```bash
    # Run locally on http://127.0.0.1:8000
    python -m app.main

    # Run with a public Gradio share link
    python -m app.main --share
    ```

    You can also specify the host and port:
    ```bash
    python -m app.main --host 0.0.0.0 --port 8000
    ```

5.  **Access the application**:
    Open your web browser and navigate to `http://127.0.0.1:8000` (or the host/port you specified).

### Option 2: Running with Docker

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/QueenDekim/pixelate-all.git
    cd pixelate-all
    ```

2.  **Build the Docker image**:
    ```bash
    docker build -t pixel-art-converter .
    ```

3.  **Run the Docker container**:
    ```bash
    docker run -p 8000:8000 pixel-art-converter
    ```

4.  **Access the application**:
    Open your web browser and navigate to `http://127.0.0.1:8000`.

## Testing

To run the tests, first install the development dependencies:

```bash
pip install -r requirements-dev.txt
```

Then, run `pytest` from the root directory:

```bash
pytest --cov=app
```

This will run all tests and generate a coverage report.

## API Documentation

Once the application is running, you can access the interactive Swagger UI documentation to explore the API endpoints.

-   **Swagger Docs**: `http://127.0.0.1:8000/docs`

This provides a clear overview of the available endpoints, parameters, and response models.

## Standalone API Usage

In addition to the Gradio interface, the application provides a standalone API endpoint at `/api/pixelate` that returns the processed file directly. This is ideal for scripting or integration with other services.

### Example with cURL

Here is an example of how to use the API with `curl` to process an image named `my_image.png`:

```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/api/pixelate' \
  -F 'file=@/path/to/your/my_image.png' \
  -F 'pixel_size=12' \
  -F 'upscale_factor=2' \
  --output pixelated_image.png
```

-   Replace `/path/to/your/my_image.png` with the actual path to your file.
-   The processed file will be saved as `pixelated_image.png` in your current directory.
