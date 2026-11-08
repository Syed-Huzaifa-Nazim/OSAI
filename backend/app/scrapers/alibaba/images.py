"""Product image extraction for Alibaba listings.

The listing record carries the product's gallery (`image.multiImage`, usually
six photos) as resized thumbnails, plus one large image. Every URL is turned
back into the original upload -- protocol added, resize suffix stripped -- and
duplicates are dropped by filename, which is a content hash.

Same shape and storage as the Daraz images: URLs only, main image first.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, List, Optional
from urllib.parse import urlparse

from . import selectors as S
from .urls import absolute_url

_RESIZE_RE = re.compile(S.IMAGE_RESIZE_SUFFIX, flags=re.I)
_IMAGE_EXTENSION_RE = re.compile(r"\.(?:jpe?g|png|webp|gif)$", flags=re.I)

SOURCE_GALLERY = "gallery"


@dataclass
class ProductImage:
    url: str
    source: str = SOURCE_GALLERY


def normalise_image_url(raw: Any) -> Optional[str]:
    """The absolute, original-resolution URL for an image reference, or None."""
    url = absolute_url(raw) if isinstance(raw, str) else None
    if not url:
        return None
    parsed = urlparse(url)
    path = _RESIZE_RE.sub(r"\1", parsed.path)
    if not _IMAGE_EXTENSION_RE.search(path):
        return None
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def image_identity(url: str) -> str:
    return urlparse(url).path.rsplit("/", 1)[-1].lower()


def extract_images(gallery: Any, big_image: Any) -> List[ProductImage]:
    """Distinct gallery photos in listing order, then the large image if new."""
    images: List[ProductImage] = []
    seen: set = set()

    def add_all(values: Iterable[Any]) -> None:
        for value in values:
            if len(images) >= S.IMAGE_MAX_PER_PRODUCT:
                return
            url = normalise_image_url(value)
            if not url:
                continue
            identity = image_identity(url)
            if identity in seen:
                continue
            seen.add(identity)
            images.append(ProductImage(url=url))

    add_all(gallery if isinstance(gallery, list) else [])
    add_all([big_image])
    return images
