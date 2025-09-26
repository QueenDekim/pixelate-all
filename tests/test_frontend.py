import pytest
import gradio as gr
from unittest.mock import patch
import os

from app.frontend import get_file_type, update_previews, upload_and_process

# Unit tests for helper functions
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

# Tests for the main processing generator
def test_upload_and_process_no_file():
    """
    Tests that an error is raised if no file is provided.
    """
    with pytest.raises(gr.Error, match="Please upload a file first!"):
        # The generator must be consumed for the code to execute
        list(upload_and_process(None, pixel_size=16, upscale_factor=1))

@patch('app.frontend.os.path.exists', return_value=True)
@patch('app.frontend.shutil.copy')
@patch('app.frontend.os.remove')
@patch('app.frontend.pixelate_image_file')
@patch('app.frontend.uuid.uuid4')
def test_upload_and_process_success(mock_uuid, mock_pixelate, mock_remove, mock_copy, mock_exists, tmp_path):
    """
    Tests the main upload and processing function with a mocked successful run.
    """
    # 1. Setup
    mock_uuid.return_value = 'test-uuid'
    file_path = str(tmp_path / "test.jpg") # Dummy input file
    
    expected_input_path = os.path.join('app/static/uploads', 'test-uuid.jpg')
    expected_output_path = os.path.join('app/static/processed', 'test-uuid_pixelated.jpg')

    # 2. Call the generator function and consume it
    gen = upload_and_process(file_path, pixel_size=16, upscale_factor=1)
    outputs = list(gen)

    # 3. Assertions
    # Check yielded values
    assert len(outputs) == 2
    
    # First yield: "Processing..."
    status_update, _, _, _ = outputs[0]
    assert status_update['value'] == "Processing..."
    assert status_update['visible'] is True

    # Final yield: "Done!"
    status_update, img_update, vid_update, dl_update = outputs[1]
    assert status_update['value'] == "Done!"
    assert img_update['value'] == expected_output_path
    assert dl_update['value'] == expected_output_path
    
    # Check mock calls
    mock_copy.assert_called_once_with(file_path, expected_input_path)
    mock_pixelate.assert_called_once_with(expected_input_path, expected_output_path, 16, 1)
    mock_exists.assert_called_once_with(expected_input_path)
    mock_remove.assert_called_once_with(expected_input_path)


@patch('app.frontend.os.path.exists', return_value=True)
@patch('app.frontend.shutil.copy')
@patch('app.frontend.os.remove')
@patch('app.frontend.pixelate_image_file')
@patch('app.frontend.uuid.uuid4')
def test_upload_and_process_failure(mock_uuid, mock_pixelate, mock_remove, mock_copy, mock_exists, tmp_path):
    """
    Tests that a Gradio error is raised when the processing function fails.
    """
    # 1. Setup
    mock_uuid.return_value = 'test-uuid'
    file_path = str(tmp_path / "test.jpg")
    expected_input_path = os.path.join('app/static/uploads', 'test-uuid.jpg')
    
    # Mock the processing function to raise an exception
    mock_pixelate.side_effect = Exception("Something went wrong")

    # 2. Call and consume the generator
    gen = upload_and_process(file_path, pixel_size=16, upscale_factor=1)
    outputs = list(gen)
    
    # 3. Assertions
    # Check yielded values
    assert len(outputs) == 2
    # The last yielded value should contain the error message
    status_update, _, _, _ = outputs[-1]
    assert "Error: Something went wrong" in status_update['value']
    assert status_update['visible'] is True

    # Check mock calls
    mock_copy.assert_called_once_with(file_path, expected_input_path)
    mock_exists.assert_called_once_with(expected_input_path)
    mock_remove.assert_called_once_with(expected_input_path)

