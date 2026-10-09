from pathlib import Path
from PIL import Image, ImageDraw


def main() -> None:
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = []
    for size in sizes:
        image = Image.new("RGBA", (size, size), "#0B1424")
        draw = ImageDraw.Draw(image)
        margin = max(2, round(size * 0.14))
        stroke = max(1, round(size * 0.035))
        draw.rounded_rectangle(
            (margin, margin, size - margin, size - margin),
            radius=max(2, round(size * 0.07)),
            outline="#35D3BE",
            width=stroke,
        )
        left = round(size * 0.29)
        right = round(size * 0.71)
        draw.line((left, round(size * 0.34), right, round(size * 0.34)), fill="#F7FAFC", width=stroke)
        draw.rectangle((left, round(size * 0.45), right, round(size * 0.57)), fill="#000000")
        draw.line((left, round(size * 0.69), round(size * 0.61), round(size * 0.69)), fill="#F7FAFC", width=stroke)
        images.append(image)
    target = Path(__file__).with_name("cic_masker.ico")
    images[-1].save(target, format="ICO", sizes=[(size, size) for size in sizes], append_images=images[:-1])


if __name__ == "__main__":
    main()

