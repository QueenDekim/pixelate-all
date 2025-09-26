import pytest
import gradio as gr
from unittest.mock import MagicMock, patch
import os
from requests.exceptions import RequestException

from app.frontend import get_file_type, update_previews, upload_and_process

# Unit tests

@pytest.mark.parametrize("file_path, expected_type", [
    ("image.jpg", "image"),
    ("test.png", "image"),
    ("document.pdf", None),
    ("archive.zip", None),
    ("video.mp4", "video"),
    ("clip.mov", "video"),
    (None, None),
    ("", None)
])
def test_get_file_type(file_path, expected_type):
    """Tests the file type detection logic."""
    assert get_file_type(file_path) == expected_type

def test_update_previews():
    """Tests the logic for updating UI previews based on file type."""
    # Test with an image file
    image_path = "/path/to/image.png"
    img_update, vid_update = update_previews(image_path)
    assert img_update['value'] == image_path
    assert img_update['visible'] is True
    assert vid_update['value'] is None
    assert vid_update['visible'] is False

    # Test with a video file
    video_path = "/path/to/video.mp4"
    img_update, vid_update = update_previews(video_path)
    assert img_update['value'] is None
    assert img_update['visible'] is False
    assert vid_update['value'] == video_path
    assert vid_update['visible'] is True

# Module/Component Test with mocks

@patch('app.frontend.requests.post')
@patch('builtins.open', new_callable=MagicMock)
def test_upload_and_process_success(mock_open, mock_post, tmp_path):
    """
    Tests the main upload and processing function with a mocked successful API call.
    """
    # 1. Setup
    file_path = str(tmp_path / "test.jpg")

    # Mock the response from the backend API
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    processed_path = os.path.abspath(str(tmp_path / "processed.jpg")) # Use absolute path
    mock_response.json.return_value = {"processed_file_path": processed_path}
    mock_post.return_value = mock_response

    # 2. Call the generator function
    gen = upload_and_process(file_path, pixel_size=16, upscale_factor=1)

    # 3. Assertions for each yield
    # First yield: Uploading
    status_update, img_update, vid_update, dl_update = next(gen)
    assert status_update['value'] == "Uploading..."
    assert status_update['visible'] is True

    # Second yield: Pixelating
    status_update, _, _, _ = next(gen)
    assert status_update['value'] == "Pixelating..."

    # Final yield: Done
    status_update, img_update, vid_update, dl_update = next(gen)
    assert status_update['value'] == "Done!"
    assert status_update['visible'] is False
    assert img_update['visible'] is True
    assert img_update['value'] == processed_path
    assert vid_update['visible'] is False
    assert dl_update['visible'] is True
    assert dl_update['value'] == processed_path


def test_upload_and_process_no_file():
    """
    Tests that an error is raised if no file is provided.
    """
    with pytest.raises(gr.Error, match="Please upload a file first!"):
        # The generator must be consumed for the code to execute
        list(upload_and_process(None, pixel_size=16, upscale_factor=1))


@patch('app.frontend.requests.post')
@patch('builtins.open', new_callable=MagicMock)
def test_upload_and_process_api_failure(mock_open, mock_post, tmp_path):
    """
    Tests that a Gradio error is raised when the API call fails.
    """
    # 1. Setup
    file_path = str(tmp_path / "test.mp4")
    mock_post.side_effect = RequestException("Connection refused")

    # 2. Call and assert
    gen = upload_and_process(file_path, pixel_size=16, upscale_factor=1)

    # Consume the generator to trigger the exception handling
    outputs = list(gen)
    
    # The last yielded value should contain the error message
    status_update, _, _, _ = outputs[-1]
    assert "Error: Connection refused" in status_update['value']
    assert status_update['visible'] is True
