import numpy as np
import pytest
import cv2
import os
from PIL import Image
import ffmpeg

from app.processing import pixelate_image, pixelate_image_file, pixelate_video_file, pixelate_gif_file

# Unit Test for the core pixelation logic
def test_pixelate_image():
    """
    Tests the core pixelate_image function with a dummy image.
    """
    # 1. Create a simple dummy image (e.g., 64x64 with 3 color channels)
    original_height, original_width = 64, 64
    # Create a gradient image to have some content to test
    original_image = np.zeros((original_height, original_width, 3), dtype=np.uint8)
    original_image[:, :, 0] = np.linspace(0, 255, original_width)  # Blue channel gradient
    original_image[:, :, 1] = np.linspace(0, 255, original_height)[:, np.newaxis] # Green channel gradient

    pixel_size = 8
    n_colors = 4 # Use a small number of colors for predictability

    # 2. Call the function to be tested
    pixelated_image = pixelate_image(original_image, pixel_size=pixel_size, n_colors=n_colors)

    # 3. Assertions
    # The output dimensions should be the same as the input
    assert pixelated_image.shape == original_image.shape, "Output image shape should match input for upscale=1."

    # Test with an upscale factor
    upscale_factor = 2
    upscaled_image = pixelate_image(original_image, pixel_size=pixel_size, n_colors=n_colors, upscale_factor=upscale_factor)
    assert upscaled_image.shape == (original_height * upscale_factor, original_width * upscale_factor, 3), "Upscaled image has incorrect dimensions."

    # The number of unique colors should be at most n_colors
    unique_colors = np.unique(pixelated_image.reshape(-1, pixelated_image.shape[2]), axis=0)
    assert len(unique_colors) <= n_colors, f"Expected at most {n_colors} colors, but found {len(unique_colors)}."

    # The upscaled image should have "blocks" of color.
    # Check if a block of size pixel_size x pixel_size has a uniform color.
    block = pixelated_image[0:pixel_size, 0:pixel_size]
    first_pixel_color = block[0, 0]
    assert np.all(block == first_pixel_color), "A block in the pixelated image should have a uniform color."

# Module Tests for file-based operations
@pytest.fixture(scope="module")
def temp_dir():
    """Create a temporary directory for test files and clean it up afterward."""
    dir_path = "tests/temp"
    os.makedirs(dir_path, exist_ok=True)
    yield dir_path
    # Cleanup
    for f in os.listdir(dir_path):
        os.remove(os.path.join(dir_path, f))
    os.rmdir(dir_path)


def test_pixelate_image_file(temp_dir):
    """
    Tests reading, processing, and writing an image file.
    """
    # 1. Create a dummy image file
    height, width = 100, 100
    input_path = os.path.join(temp_dir, "test_image.png")
    output_path = os.path.join(temp_dir, "test_image_pixelated.png")
    dummy_image = np.zeros((height, width, 3), dtype=np.uint8)
    cv2.imwrite(input_path, dummy_image)
    upscale_factor = 2

    # 2. Call the function
    pixelate_image_file(input_path, output_path, pixel_size=10, upscale_factor=upscale_factor)

    # 3. Assertions
    # Check if the output file was created
    assert os.path.exists(output_path), "Output file was not created."

    # Check if the output file is a valid image with upscaled dimensions
    result_img = cv2.imread(output_path)
    assert result_img is not None, "Output file is not a valid image."
    assert result_img.shape == (height * upscale_factor, width * upscale_factor, 3), "Output image has incorrect upscaled dimensions."


def test_pixelate_image_file_invalid_input():
    """
    Tests if pixelate_image_file raises an error for a non-existent file.
    """
    with pytest.raises(ValueError, match="Could not read the image file."):
        pixelate_image_file("non_existent_file.png", "output.png", upscale_factor=1)


def create_dummy_video_with_audio(path, width, height, fps, duration):
    """Helper to create a video with a silent audio track using ffmpeg."""
    # Generate a dummy video stream
    video_input = ffmpeg.input(f'testsrc=size={width}x{height}:rate={fps}', f='lavfi', t=duration)
    # Generate a dummy audio stream
    audio_input = ffmpeg.input('anullsrc', f='lavfi', t=duration)
    # Mux them together
    ffmpeg.output(video_input, audio_input, path, vcodec='libx264', acodec='aac', strict='experimental').run(overwrite_output=True, quiet=True)

def create_dummy_video_no_audio(path, width, height, fps, duration):
    """Helper to create a video without an audio track using ffmpeg."""
    video_input = ffmpeg.input(f'testsrc=size={width}x{height}:rate={fps}', f='lavfi', t=duration)
    ffmpeg.output(video_input, path, vcodec='libx264').run(overwrite_output=True, quiet=True)

@pytest.mark.parametrize("with_audio", [True, False])
def test_pixelate_video_file(temp_dir, with_audio):
    """Tests processing a video file, ensuring audio is preserved if present."""
    if with_audio:
        input_path = os.path.join(temp_dir, "test_video_with_audio.mp4")
        create_dummy_video_with_audio(input_path, 128, 72, 24, 1)
    else:
        input_path = os.path.join(temp_dir, "test_video_no_audio.mp4")
        create_dummy_video_no_audio(input_path, 128, 72, 24, 1)

    output_path = os.path.join(temp_dir, "test_video_pixelated.mp4")
    upscale_factor = 2

    pixelate_video_file(input_path, output_path, pixel_size=16, upscale_factor=upscale_factor)

    assert os.path.exists(output_path), "Output video file was not created."

    # Verify output video properties using ffmpeg.probe
    probe = ffmpeg.probe(output_path)
    video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
    audio_stream = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)

    assert video_stream is not None
    assert video_stream['codec_name'] == 'h264' # Check for web-compatible codec
    assert int(video_stream['width']) == 128 * upscale_factor
    assert int(video_stream['height']) == 72 * upscale_factor

    if with_audio:
        assert audio_stream is not None, "Audio stream should be preserved."
    else:
        assert audio_stream is None, "No audio stream should be present."

def test_pixelate_video_file_invalid_input():
    """
    Tests if pixelate_video_file raises an error for a non-existent file.
    """
    with pytest.raises(RuntimeError, match="Failed during video processing"):
        pixelate_video_file("non_existent_video.mp4", "output.mp4", upscale_factor=1)

def test_pixelate_gif_file(temp_dir):
    """Tests reading, processing, and writing an animated GIF file."""
    # 1. Create a dummy animated GIF
    input_path = os.path.join(temp_dir, "test_anim.gif")
    output_path = os.path.join(temp_dir, "test_anim_pixelated.gif")
    n_frames = 3
    width, height = 64, 64
    frames = []
    for i in range(n_frames):
        # Create a simple frame that changes color
        arr = np.full((height, width, 3), (i * 50, i * 25, 255 - i * 50), dtype=np.uint8)
        frames.append(Image.fromarray(arr, 'RGB'))

    frames[0].save(input_path, save_all=True, append_images=frames[1:], duration=100, loop=0)

    # 2. Call the function
    pixelate_gif_file(input_path, output_path, pixel_size=8, upscale_factor=2)

    # 3. Assertions
    assert os.path.exists(output_path), "Output GIF file was not created."

    # Check if the output is a valid GIF and has the correct number of frames
    with Image.open(output_path) as result_gif:
        assert result_gif.format == 'GIF', "Output file is not in GIF format."
        assert result_gif.is_animated, "Output GIF is not animated."
        assert result_gif.n_frames == n_frames, "Output GIF has an incorrect number of frames."
        assert result_gif.width == width * 2
        assert result_gif.height == height * 2
