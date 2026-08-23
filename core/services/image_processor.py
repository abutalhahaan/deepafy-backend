from io import BytesIO
from uuid import uuid4

from django.core.files.base import ContentFile
from PIL import Image, ImageOps


IMAGE_PRESETS = {
    "profile": {
        "width": 800,
        "height": 800,
        "max_size_kb": 500,
        "quality": 85,
    },
    "cover": {
        "width": 1500,
        "height": 500,
        "max_size_kb": 1024,
        "quality": 85,
    },
}


def process_image(uploaded_file, preset):
    """
    Process an uploaded image using a predefined preset.

    Steps:
    1. Validate image
    2. Fix EXIF orientation
    3. Convert to RGB
    4. Resize and center-crop
    5. Convert to WebP
    6. Compress until target size is reached
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

    except Exception as error:
        raise ValueError(
            "The uploaded file is not a valid image."
        ) from error

    image = ImageOps.exif_transpose(image)

    if image.mode in ("RGBA", "LA"):
        background = Image.new(
            "RGB",
            image.size,
            "white",
        )

        alpha = image.getchannel("A")

        background.paste(
            image,
            mask=alpha,
        )

        image = background

    elif image.mode != "RGB":
        image = image.convert("RGB")

    image = ImageOps.fit(
        image,
        (target_width, target_height),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )

    output = BytesIO()

    current_quality = quality

    while current_quality >= 40:
        output.seek(0)
        output.truncate(0)

        image.save(
            output,
            format="WEBP",
            quality=current_quality,
            method=6,
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

    filename = f"{preset}_{uuid4().hex}.webp"

    return ContentFile(
        output.read(),
        name=filename,
    )