import base64
from io import BytesIO

from PIL import Image

from discordbot.services.image_preprocessor import ImagePreprocessor


def build_png_bytes(*, width: int, height: int) -> bytes:
    image = Image.new("RGB", (width, height), color="red")
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_is_supported_attachment_accepts_known_image_types() -> None:
    preprocessor = ImagePreprocessor(max_pixels=2073600)

    assert preprocessor.is_supported_attachment(
        content_type="image/png",
        filename="sample.png",
    )


def test_is_supported_attachment_falls_back_to_filename_extension() -> None:
    preprocessor = ImagePreprocessor(max_pixels=2073600)

    assert preprocessor.is_supported_attachment(
        content_type=None,
        filename="sample.webp",
    )


def test_encode_for_ollama_resizes_large_images() -> None:
    preprocessor = ImagePreprocessor(max_pixels=10000)
    raw_bytes = build_png_bytes(width=400, height=200)

    encoded = preprocessor.encode_for_ollama(raw_bytes)
    normalized_bytes = base64.b64decode(encoded)
    with Image.open(BytesIO(normalized_bytes)) as image:
        assert image.width * image.height <= 10000
        assert image.width < 400
        assert image.height < 200
