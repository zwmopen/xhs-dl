"""Human-readable, cross-platform media filenames."""

import re
from pathlib import Path


def safe_title(value, limit=64):
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(value or "")).strip(" .-")
    return (cleaned or "未命名作品")[:limit]


def media_filename(index, title, extension, is_video=False):
    extension = "." + str(extension or "").lstrip(".").lower()
    if is_video:
        label = "视频" if index == 0 else f"视频{index + 1}"
    else:
        label = "封面" if index == 0 else f"内页{index}"
    return f"{label}-{safe_title(title)}{extension}"


def convert_image_file(path, output_format):
    path = Path(path)
    output_format = str(output_format or "jpg").lower()
    if output_format == "keep":
        return path
    if output_format not in {"jpg", "png"}:
        raise ValueError(f"不支持的图片格式：{output_format}")

    from PIL import Image

    target = path.with_suffix("." + output_format)
    temporary = target.with_name(target.stem + ".converting" + target.suffix)
    with Image.open(path) as image:
        if output_format == "jpg":
            if image.mode in {"RGBA", "LA"}:
                background = Image.new("RGB", image.size, "white")
                background.paste(image.convert("RGB"), mask=image.getchannel("A"))
                image = background
            else:
                image = image.convert("RGB")
            image.save(temporary, "JPEG", quality=95, subsampling=0)
        else:
            image.save(temporary, "PNG", optimize=True)
    temporary.replace(target)
    if target != path and path.exists():
        path.unlink()
    return target
