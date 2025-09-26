import pytest
from fastapi.testclient import TestClient
import os
import shutil
import numpy as np
import cv2
from unittest.mock import patch

from app.main import app

client = TestClient(app)

TEST_UPLOADS_DIR = "app/static/uploads_test"
TEST_PROCESSED_DIR = "app/static/processed_test"

@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown_dirs():
    from app import main
    main.UPLOADS_DIR = TEST_UPLOADS_DIR
    main.PROCESSED_DIR = TEST_PROCESSED_DIR

    os.makedirs(TEST_UPLOADS_DIR, exist_ok=True)
    os.makedirs(TEST_PROCESSED_DIR, exist_ok=True)

    yield

    shutil.rmtree(TEST_UPLOADS_DIR)
    shutil.rmtree(TEST_PROCESSED_DIR)

def create_dummy_image(path: str, width=32, height=32):
    img = np.zeros((height, width, 3), dtype=np.uint8)
    cv2.imwrite(path, img)

def create_dummy_video(path: str, width=32, height=32, fps=24, duration_sec=1):
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(path, fourcc, fps, (width, height))
    for i in range(fps * duration_sec):
        # Create a simple frame that changes over time for predictability
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:, :, 0] = (i * 10) % 256 # Blue channel changes
        frame[:, :, 1] = (i * 5) % 256  # Green channel changes
        out.write(frame)
    out.release()

def test_upload_and_process_image():
    width, height = 32, 32
    upscale_factor = 2
    dummy_image_path = os.path.join(TEST_UPLOADS_DIR, "dummy_for_upload.png")
    create_dummy_image(dummy_image_path, width=width, height=height)

    with open(dummy_image_path, "rb") as f:
        files = {'file': ('test_image.png', f, 'image/png')}
        data = {'pixel_size': '8', 'upscale_factor': str(upscale_factor)}
        response = client.post("/upload/", files=files, data=data)

    assert response.status_code == 200
    response_json = response.json()
    assert "processed_file_path" in response_json

    processed_path = response_json["processed_file_path"]
    assert os.path.exists(processed_path)
    assert TEST_PROCESSED_DIR in processed_path

    result_img = cv2.imread(processed_path)
    assert result_img is not None
    assert result_img.shape == (height * upscale_factor, width * upscale_factor, 3)

def test_upload_and_process_video():
    width, height = 32, 32
    upscale_factor = 2
    dummy_video_path = os.path.join(TEST_UPLOADS_DIR, "dummy_for_upload.mp4")
    create_dummy_video(dummy_video_path, width=width, height=height)

    with open(dummy_video_path, "rb") as f:
        files = {'file': ('test_video.mp4', f, 'video/mp4')}
        data = {'pixel_size': '16', 'upscale_factor': str(upscale_factor)}
        response = client.post("/upload/", files=files, data=data)

    assert response.status_code == 200
    response_json = response.json()
    assert "processed_file_path" in response_json

    processed_path = response_json["processed_file_path"]
    assert os.path.exists(processed_path)
    assert TEST_PROCESSED_DIR in processed_path

    cap = cv2.VideoCapture(processed_path)
    assert cap.isOpened()
    assert int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) == width * upscale_factor
    assert int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) == height * upscale_factor
    cap.release()

@patch('app.main.run_in_threadpool', side_effect=Exception("Processing failed!"))
def test_processing_error_500(mock_run_in_threadpool):
    dummy_image_path = os.path.join(TEST_UPLOADS_DIR, "dummy_for_500_error.png")
    create_dummy_image(dummy_image_path)

    with open(dummy_image_path, "rb") as f:
        files = {'file': ('test_image_500.png', f, 'image/png')}
        data = {'pixel_size': '8', 'upscale_factor': '1'}
        response = client.post("/upload/", files=files, data=data)

    assert response.status_code == 500
    assert "Error during processing: Processing failed!" in response.json()["detail"]

def test_upload_invalid_file_details():
    dummy_image_path = os.path.join(TEST_UPLOADS_DIR, "dummy_for_invalid.png")
    create_dummy_image(dummy_image_path)

    with open(dummy_image_path, "rb") as f:
        # When filename is None, FastAPI's validation should fail first.
        files = {'file': (None, f, 'image/png')}
        response = client.post("/upload/", files=files, data={'pixel_size': '8'})

    # Expect 422 Unprocessable Entity, which is FastAPI's standard validation error
    assert response.status_code == 422

def test_upload_unsupported_file_type():
    dummy_text_path = os.path.join(TEST_UPLOADS_DIR, "dummy.txt")
    with open(dummy_text_path, "w") as f:
        f.write("this is not an image")

    with open(dummy_text_path, "rb") as f:
        files = {'file': ('test.txt', f, 'text/plain')}
        response = client.post("/upload/", files=files)

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported file type"

def test_upload_no_file():
    response = client.post("/upload/", data={'pixel_size': '8'})
    assert response.status_code == 422
