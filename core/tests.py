from io import BytesIO

from django.test import TestCase
from PIL import Image

from core.services.image_processor import IMAGE_PRESETS, process_image


class ImageProcessorTests(TestCase):
    def create_test_image(self, image_format, size=(1200, 800), mode="RGB"):
        image = Image.new(mode, size, (120, 180, 220))

        output = BytesIO()

        save_kwargs = {}

        if image_format == "JPEG":
            save_kwargs["quality"] = 95
        elif image_format == "WEBP":
            save_kwargs["quality"] = 95

        image.save(output, format=image_format, **save_kwargs)
        output.seek(0)

        return output

    def test_jpeg_processing_for_all_presets(self):
        for preset, settings in IMAGE_PRESETS.items():
            with self.subTest(preset=preset):
                uploaded_file = self.create_test_image("JPEG")

                result = process_image(uploaded_file, preset)

                result.seek(0)
                processed_image = Image.open(result)

                self.assertEqual(
                    processed_image.size,
                    (settings["width"], settings["height"]),
                )
                self.assertEqual(processed_image.format, "JPEG")
                self.assertTrue(result.name.endswith(".jpg"))
                self.assertLessEqual(result.size, 2 * 1024 * 1024)

    def test_png_processing_for_all_presets(self):
        for preset, settings in IMAGE_PRESETS.items():
            with self.subTest(preset=preset):
                uploaded_file = self.create_test_image("PNG")

                result = process_image(uploaded_file, preset)

                result.seek(0)
                processed_image = Image.open(result)

                self.assertEqual(
                    processed_image.size,
                    (settings["width"], settings["height"]),
                )
                self.assertEqual(processed_image.format, "PNG")
                self.assertTrue(result.name.endswith(".png"))
                self.assertLessEqual(result.size, 2 * 1024 * 1024)

    def test_webp_processing_for_all_presets(self):
        for preset, settings in IMAGE_PRESETS.items():
            with self.subTest(preset=preset):
                uploaded_file = self.create_test_image("WEBP")

                result = process_image(uploaded_file, preset)

                result.seek(0)
                processed_image = Image.open(result)

                self.assertEqual(
                    processed_image.size,
                    (settings["width"], settings["height"]),
                )
                self.assertEqual(processed_image.format, "WEBP")
                self.assertTrue(result.name.endswith(".webp"))
                self.assertLessEqual(result.size, 2 * 1024 * 1024)

    def test_png_transparency_is_preserved(self):
        image = Image.new("RGBA", (1200, 800), (120, 180, 220, 120))

        uploaded_file = BytesIO()
        image.save(uploaded_file, format="PNG")
        uploaded_file.seek(0)

        result = process_image(uploaded_file, "profile")

        result.seek(0)
        processed_image = Image.open(result)

        self.assertEqual(processed_image.format, "PNG")
        self.assertIn("A", processed_image.mode)
        self.assertEqual(processed_image.size, (800, 800))

    def test_invalid_image_is_rejected(self):
        uploaded_file = BytesIO(b"this is not an image")
        uploaded_file.name = "invalid.jpg"

        with self.assertRaises(ValueError):
            process_image(uploaded_file, "profile")

    def test_unsupported_image_format_is_rejected(self):
        uploaded_file = BytesIO()

        image = Image.new("RGB", (100, 100), (120, 180, 220))
        image.save(uploaded_file, format="BMP")
        uploaded_file.seek(0)

        with self.assertRaises(ValueError):
            process_image(uploaded_file, "profile")

    def test_unknown_preset_is_rejected(self):
        uploaded_file = self.create_test_image("JPEG")

        with self.assertRaises(ValueError):
            process_image(uploaded_file, "unknown")