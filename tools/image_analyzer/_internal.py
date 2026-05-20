import hashlib
import os
from typing import Any, Dict, Tuple

import aiohttp
from astrbot.api import logger

PREPROCESS_CONFIG = {
    "ocr": {"max_size": 2048, "format": "PNG", "grayscale": True},
    "search": {"max_size": 1024, "format": "JPEG", "quality": 85},
    "vision": {"max_size": 2048, "format": "JPEG", "quality": 90},
}


async def download_image(image_url: str, save_dir: str) -> str:
    if image_url.startswith(("http://", "https://")):
        os.makedirs(save_dir, exist_ok=True)
        filename = hashlib.md5(image_url.encode()).hexdigest()
        save_path = os.path.join(save_dir, filename + ".jpg")

        if os.path.exists(save_path):
            return save_path

        async with aiohttp.ClientSession() as session:
            async with session.get(
                image_url, timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"图片下载失败: HTTP {resp.status}")
                data = await resp.read()

        with open(save_path, "wb") as f:
            f.write(data)
        return save_path

    elif image_url.startswith("base64://"):
        import base64

        os.makedirs(save_dir, exist_ok=True)
        raw = image_url[len("base64://") :]
        data = base64.b64decode(raw)
        filename = hashlib.md5(data).hexdigest()
        save_path = os.path.join(save_dir, filename + ".jpg")
        with open(save_path, "wb") as f:
            f.write(data)
        return save_path

    elif os.path.isfile(image_url):
        return image_url

    else:
        raise FileNotFoundError(f"图片未找到: {image_url}")


def preprocess_image(image_path: str, task_type: str, output_dir: str) -> str:
    from PIL import Image

    config = PREPROCESS_CONFIG.get(task_type, PREPROCESS_CONFIG["vision"])

    img = Image.open(image_path)

    if config.get("grayscale") and task_type == "ocr":
        img = img.convert("L")
    else:
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

    max_size = config["max_size"]
    if max(img.size) > max_size:
        ratio = max_size / max(img.size)
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        img = img.resize(new_size, Image.LANCZOS)

    os.makedirs(output_dir, exist_ok=True)
    basename = os.path.splitext(os.path.basename(image_path))[0]
    output_format = config["format"]
    ext = "." + output_format.lower()
    output_path = os.path.join(output_dir, basename + "_preprocessed" + ext)

    save_kwargs: Dict[str, Any] = {"format": output_format}
    if output_format == "JPEG":
        save_kwargs["quality"] = config.get("quality", 85)
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")

    img.save(output_path, **save_kwargs)
    return output_path


def compute_image_hashes(image_path: str, hash_size: int = 8) -> Tuple[str, str]:
    with open(image_path, "rb") as f:
        image_data = f.read()
    md5 = hashlib.md5(image_data).hexdigest()

    dhash_str = ""
    try:
        from imgdd import dhash
        from PIL import Image

        img = Image.open(image_path)
        dhash_str = dhash(img, hash_size=hash_size)
    except ImportError:
        logger.warning("[nekokit.cateye] imgdd 未安装，dHash 已禁用")
    except Exception as e:
        logger.warning(f"[nekokit.cateye] dHash 计算失败: {e}")

    return md5, dhash_str


def image_to_base64_url(image_path: str) -> str:
    import base64

    ext = os.path.splitext(image_path)[1].lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    mime = mime_map.get(ext, "image/jpeg")

    with open(image_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{b64}"


# TODO: 实现日志压缩
def compress_logs():
    pass
