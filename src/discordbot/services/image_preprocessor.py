from __future__ import annotations

import base64
from io import BytesIO
from math import sqrt

from PIL import Image


SUPPORTED_IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}
SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class ImagePreprocessorError(RuntimeError):
    pass


class ImagePreprocessor:
    def __init__(self, *, max_pixels: int) -> None:
        self._max_pixels = max_pixels

    def is_supported_attachment(
        self,
        *,
        content_type: str | None,
        filename: str,
    ) -> bool:
        normalized_content_type = (content_type or "").strip().lower()
        if normalized_content_type in SUPPORTED_IMAGE_CONTENT_TYPES:
            return True
        lower_filename = filename.lower()
        return any(lower_filename.endswith(extension) for extension in SUPPORTED_IMAGE_EXTENSIONS)

    def encode_for_ollama(self, raw_bytes: bytes) -> str:
        try:
            with Image.open(BytesIO(raw_bytes)) as image:
                normalized_image = self._resize_if_needed(image)
                output = BytesIO()
                normalized_image.save(output, format="PNG", optimize=True)
        except OSError as exc:
            raise ImagePreprocessorError("Failed to preprocess image attachment.") from exc
        return base64.b64encode(output.getvalue()).decode("ascii")

    def _resize_if_needed(self, image: Image.Image) -> Image.Image:
        current_pixels = image.width * image.height
        if current_pixels <= self._max_pixels:
            return image.copy()

        scale = sqrt(self._max_pixels / current_pixels)
        new_width = max(int(image.width * scale), 1)
        new_height = max(int(image.height * scale), 1)
        resized = image.copy()
        resized.thumbnail((new_width, new_height), Image.Resampling.LANCZOS)
        return resized
