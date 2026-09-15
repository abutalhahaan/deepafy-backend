import re
import bleach
from bleach.css_sanitizer import CSSSanitizer


ALLOWED_TAGS = [
    "p",
    "br",
    "strong",
    "em",
    "u",
    "s",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "ul",
    "ol",
    "li",
    "blockquote",
    "code",
    "pre",
    "span",
    "mark",
    "a",
    "img",
]


ALLOWED_ATTRIBUTES = {
    "p": ["style"],
    "h1": ["style"],
    "h2": ["style"],
    "h3": ["style"],
    "h4": ["style"],
    "h5": ["style"],
    "h6": ["style"],

    "span": ["style"],
    "mark": ["style", "data-color"],
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title", "width", "height", "data-width"],
}


ALLOWED_CSS_PROPERTIES = [
    "color",
    "background-color",
    "font-family",
    "font-size",
    "font-weight",
    "font-style",
    "text-decoration",
    "text-align",
    "width",
    "height",
]


CSS_SANITIZER = CSSSanitizer(allowed_css_properties=ALLOWED_CSS_PROPERTIES)


ALLOWED_PROTOCOLS = [
    "http",
    "https",
    "mailto",
]


def sanitize_html(value: str) -> str:
    """
    Sanitize user-generated HTML while preserving
    the formatting supported by Deepafy's rich text editor.
    """
    if not value:
        return ""

    value = re.sub(r"<\s*(script|style)\b[^>]*>.*?<\s*/\s*\1\s*>", "", value, flags=re.IGNORECASE | re.DOTALL)

    return bleach.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
        strip_comments=True,
        css_sanitizer=CSS_SANITIZER,
    )
