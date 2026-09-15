from django.test import SimpleTestCase

from core.services.html_sanitizer import sanitize_html


class HtmlSanitizerTests(SimpleTestCase):
    def test_safe_rich_text_is_preserved(self):
        html = (
            '<p style="color:red;text-align:center">'
            'Hello <strong>Deepafy</strong> <u>World</u>'
            '</p>'
        )

        result = sanitize_html(html)

        self.assertIn("<strong>Deepafy</strong>", result)
        self.assertIn("<u>World</u>", result)
        self.assertIn('color:red', result)
        self.assertIn('text-align:center', result)

    def test_script_tag_and_content_are_removed(self):
        html = '<p>Hello</p><script>alert(1)</script><p>World</p>'

        result = sanitize_html(html)

        self.assertNotIn("<script", result.lower())
        self.assertNotIn("alert(1)", result)
        self.assertIn("<p>Hello</p>", result)
        self.assertIn("<p>World</p>", result)

    def test_event_handler_is_removed(self):
        html = '<img src="https://example.com/image.jpg" onerror="alert(1)">'

        result = sanitize_html(html)

        self.assertIn('src="https://example.com/image.jpg"', result)
        self.assertNotIn("onerror", result.lower())
        self.assertNotIn("alert(1)", result)

    def test_dangerous_css_is_removed(self):
        html = (
            '<p style="color:red;position:fixed;'
            'background-color:yellow">Hello</p>'
        )

        result = sanitize_html(html)

        self.assertIn("color:red", result)
        self.assertIn("background-color:yellow", result)
        self.assertNotIn("position", result.lower())

    def test_unsafe_url_protocol_is_removed(self):
        html = '<a href="javascript:alert(1)">Click</a>'

        result = sanitize_html(html)

        self.assertNotIn("javascript:", result.lower())
        self.assertNotIn("alert(1)", result)
