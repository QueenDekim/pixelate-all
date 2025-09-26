import cv2
import numpy as np
from PIL import Image
import ffmpeg as ffmpeg_python
import os

def pixelate_image(image: np.ndarray, pixel_size: int = 16, n_colors: int = 16, upscale_factor: int = 1) -> np.ndarray:
    """Pixelates an image, reduces its color palette, and preserves transparency."""
    has_alpha = image.shape[2] == 4
    if has_alpha:
        bgr = image[:, :, :3]
        alpha = image[:, :, 3]
    else:
        bgr = image
        alpha = None

    height, width, _ = bgr.shape
    if height == 0 or width == 0:
        return image

    small_height = max(1, height // pixel_size)
    small_width = max(1, width // pixel_size)
    small_bgr = cv2.resize(bgr, (small_width, small_height), interpolation=cv2.INTER_LINEAR)

    pixels = np.float32(small_bgr.reshape((-1, 3)))
    num_pixels = pixels.shape[0]
    effective_n_colors = min(n_colors, num_pixels)

    if effective_n_colors < 1:
        quantized_small_bgr = small_bgr
    else:
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
        _, labels, centers = cv2.kmeans(pixels, effective_n_colors, None, criteria, 10, cv2.KMEANS_PP_CENTERS)
        centers = np.uint8(centers)
        quantized_pixels = centers[labels.flatten()]
        quantized_small_bgr = quantized_pixels.reshape(small_bgr.shape)

    final_height = height * upscale_factor
    final_width = width * upscale_factor
    pixelated_bgr = cv2.resize(quantized_small_bgr, (final_width, final_height), interpolation=cv2.INTER_NEAREST)

    if has_alpha and alpha is not None:
        small_alpha = cv2.resize(alpha, (small_width, small_height), interpolation=cv2.INTER_LINEAR)
        pixelated_alpha = cv2.resize(small_alpha, (final_width, final_height), interpolation=cv2.INTER_NEAREST)
        pixelated_img = cv2.merge([pixelated_bgr, pixelated_alpha])
    else:
        pixelated_img = pixelated_bgr

    return pixelated_img

def pixelate_image_file(input_path: str, output_path: str, pixel_size: int = 16, upscale_factor: int = 1):
    """Reads an image file, pixelates it, and saves the result, preserving transparency."""
    img = cv2.imread(input_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError("Could not read the image file.")

    pixelated_img = pixelate_image(img, pixel_size=pixel_size, upscale_factor=upscale_factor)
    cv2.imwrite(output_path, pixelated_img)

def pixelate_gif_file(input_path: str, output_path: str, pixel_size: int = 16, upscale_factor: int = 1):
    """Reads an animated GIF, pixelates each frame, and saves the new GIF, preserving transparency."""
    with Image.open(input_path) as img:
        if not getattr(img, 'is_animated', False):
            frame_rgba = img.convert("RGBA")
            frame_cv = np.array(frame_rgba)
            frame_bgra = cv2.cvtColor(frame_cv, cv2.COLOR_RGBA2BGRA)
            pixelated_frame_bgra = pixelate_image(frame_bgra, pixel_size, upscale_factor=upscale_factor)
            pixelated_frame_rgba = cv2.cvtColor(pixelated_frame_bgra, cv2.COLOR_BGRA2RGBA)
            Image.fromarray(pixelated_frame_rgba).save(output_path, 'GIF')
            return

        frames = []
        durations = []
        for i in range(img.n_frames):
            img.seek(i)
            durations.append(img.info.get('duration', 100))

            frame_rgba = img.convert("RGBA")
            frame_cv = np.array(frame_rgba)
            frame_bgra = cv2.cvtColor(frame_cv, cv2.COLOR_RGBA2BGRA)

            pixelated_frame_bgra = pixelate_image(frame_bgra, pixel_size, upscale_factor=upscale_factor)
            
            pixelated_frame_rgba = cv2.cvtColor(pixelated_frame_bgra, cv2.COLOR_BGRA2RGBA)
            pil_frame = Image.fromarray(pixelated_frame_rgba)
            frames.append(pil_frame)

        if frames:
            frames[0].save(
                output_path,
                save_all=True,
                append_images=frames[1:],
                duration=durations,
                loop=0,
                optimize=False,
                disposal=2
            )

def pixelate_video_file(input_path: str, output_path: str, pixel_size: int = 16, upscale_factor: int = 1):
    """Reads a video, pixelates each frame, and saves it using a robust ffmpeg pipeline."""
    try:
        probe = ffmpeg_python.probe(input_path)
        video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
        width = int(video_info['width'])
        height = int(video_info['height'])
        fps = eval(video_info['r_frame_rate'])
        has_audio = any(s['codec_type'] == 'audio' for s in probe['streams'])

        upscaled_width = width * upscale_factor
        upscaled_height = height * upscale_factor

        # Setup ffmpeg process
        input_kwargs = {'format': 'rawvideo', 'pix_fmt': 'bgr24', 's': f'{upscaled_width}x{upscaled_height}'}
        input_stream = ffmpeg_python.input('pipe:', **input_kwargs, r=fps)

        output_streams = [input_stream.video]
        if has_audio:
            audio_stream = ffmpeg_python.input(input_path).audio
            output_streams.append(audio_stream)

        process = (
            ffmpeg_python.output(*output_streams, output_path, vcodec='libx264', acodec='aac' if has_audio else 'copy', pix_fmt='yuv420p', shortest=None)
            .overwrite_output()
            .run_async(pipe_stdin=True, quiet=True)
        )

        # Process frames with OpenCV and pipe to ffmpeg
        cap = cv2.VideoCapture(input_path)
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            pixelated_frame = pixelate_image(frame, pixel_size, upscale_factor=upscale_factor)
            process.stdin.write(pixelated_frame.tobytes())

        process.stdin.close()
        process.wait()
        cap.release()

    except Exception as e:
        raise RuntimeError(f"Failed during video processing: {e}")
