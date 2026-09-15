from .image_processor import process_image


def process_editor_image(uploaded_file):
    """
    Process an image uploaded for rich-text/editor content.
    Preserves the original aspect ratio while limiting dimensions
    and compressing the resulting file.
    """
    return process_image(uploaded_file, preset="editor")
