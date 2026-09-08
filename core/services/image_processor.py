from io import BytesIO
from uuid import uuid4

from django.core.files.base import ContentFile
from PIL import Image, ImageOps


IMAGE_PRESETS = {
    "profile": {
        "width": 800,
        "height": 800,
        "max_size_kb": 800,
        "quality": 85,
    },
    "cover": {
        "width": 1500,
        "height": 500,
        "max_size_kb": 2048,
        "quality": 85,
    },

    "background": {
        "width": 1920,
        "height": 1080,
        "max_size_kb": 2048,
        "quality": 85,
    },    
}


def process_image(uploaded_file, preset):
    """
    Process an uploaded image using a predefined preset.

    Steps:
    1. Validate image format
    2. Fix EXIF orientation
    3. Preserve supported image format and transparency
    4. Resize and center-crop to exact preset dimensions
    5. Compress within the maximum file size
    6. Return the processed image
    """

    if preset not in IMAGE_PRESETS:
        raise ValueError(f"Unknown image preset: {preset}")

    settings = IMAGE_PRESETS[preset]

    target_width = settings["width"]
    target_height = settings["height"]
    max_size_bytes = settings["max_size_kb"] * 1024
    quality = settings["quality"]

    try:
        image = Image.open(uploaded_file)
        image.verify()

        uploaded_file.seek(0)
        image = Image.open(uploaded_file)

        if image.format not in ("JPEG", "PNG", "WEBP"):
            raise ValueError(
                "Only JPG, JPEG, PNG, and WebP images are supported."
            )

    except Exception as error:
        raise ValueError(
            "The uploaded file is not a valid image."
        ) from error

    image_format = image.format

    image = ImageOps.exif_transpose(image)

    if image_format == "JPEG":
        if image.mode != "RGB":
            image = image.convert("RGB")
    elif image_format == "PNG":
        if image.mode not in ("RGB", "RGBA", "L", "LA"):
            image = image.convert("RGBA")
    elif image_format == "WEBP":
        if image.mode not in ("RGB", "RGBA", "L", "LA"):
            image = image.convert("RGBA")

    image = ImageOps.fit(
        image,
        (target_width, target_height),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )
    output = BytesIO()
    current_quality = quality

    while current_quality >= 20:
        output.seek(0)
        output.truncate(0)

        if image_format == "PNG":
            image.save(
                output,
                format="PNG",
                optimize=True,
            )
            break
        elif image_format == "WEBP":
            image.save(
                output,
                format="WEBP",
                quality=current_quality,
                method=6,
            )
        else:
            image.save(
                output,
                format="JPEG",
                quality=current_quality,
                optimize=True,
                progressive=True,
            )

        if output.tell() <= max_size_bytes:
            break

        current_quality -= 5

    if output.tell() > max_size_bytes:
        raise ValueError(
            "Unable to compress the image "
            "to the required file size."
        )

    output.seek(0)

    extension = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}[image_format]
    filename = f"{preset}_{uuid4().hex}.{extension}"

    return ContentFile(
        output.read(),
        name=filename,
    )