"""Genera app_icon.ico cuadrado y multi-resolución para Windows/PyInstaller."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ASSETS_DIR = Path(__file__).resolve().parents[1] / "src" / "app_s3" / "assets"
PNG_PATH = ASSETS_DIR / "app_icon.png"
ICO_PATH = ASSETS_DIR / "app_icon.ico"
ICON_SIZES = (256, 128, 64, 48, 32, 16)


def _square_icon(source: Image.Image, size: int) -> Image.Image:
    """Escala la imagen y la centra en un lienzo cuadrado con transparencia."""
    rgba = source.convert("RGBA")
    width, height = rgba.size
    scale = min(size / width, size / height)
    new_width = max(1, int(width * scale))
    new_height = max(1, int(height * scale))
    resized = rgba.resize((new_width, new_height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    offset = ((size - new_width) // 2, (size - new_height) // 2)
    canvas.paste(resized, offset, resized)
    return canvas


def generate_ico(png_path: Path = PNG_PATH, ico_path: Path = ICO_PATH) -> Path:
    if not png_path.exists():
        raise FileNotFoundError(f"No se encontró el PNG de origen: {png_path}")

    source = Image.open(png_path)
    frames = [_square_icon(source, size) for size in ICON_SIZES]
    ico_path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        ico_path,
        format="ICO",
        sizes=[(frame.width, frame.height) for frame in frames],
        append_images=frames[1:],
    )
    return ico_path


if __name__ == "__main__":
    output = generate_ico()
    print(f"Icono generado: {output}")
