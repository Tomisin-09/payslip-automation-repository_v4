from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Tuple

from PIL import Image


@dataclass(frozen=True)
class AssetSpec:
    path: Path
    allowed_extensions: Tuple[str, ...]
    enforce_resolution: bool
    required_px: Optional[Tuple[int, int]]
    label: str


def validate_asset(spec: AssetSpec) -> None:
    p = spec.path.resolve()
    if not p.exists():
        raise FileNotFoundError(f"Missing required asset '{spec.label}': {p}")

    ext = p.suffix.lower()
    if spec.allowed_extensions and ext not in {e.lower() for e in spec.allowed_extensions}:
        raise ValueError(
            f"Asset '{spec.label}' has invalid extension '{ext}'. Allowed: {sorted(spec.allowed_extensions)}"
        )

    if spec.enforce_resolution:
        if not spec.required_px:
            raise ValueError(f"Asset '{spec.label}' enforce_resolution=True but required_px not set")
        w_req, h_req = spec.required_px
        with Image.open(str(p)) as im:
            w, h = im.size
        if (w, h) != (w_req, h_req):
            raise ValueError(
                f"Asset '{spec.label}' resolution is {w}x{h}px. Required: {w_req}x{h_req}px"
            )


def validate_branding_assets(
    logo_path: Path,
    signature_path: Path,
    allowed_extensions: Iterable[str] = (".png", ".jpg", ".jpeg"),
    enforce_resolution: bool = False,
    logo_required_px: Optional[Tuple[int, int]] = None,
    signature_required_px: Optional[Tuple[int, int]] = None,
) -> None:
    allowed_extensions = tuple(allowed_extensions)

    validate_asset(
        AssetSpec(
            path=logo_path,
            allowed_extensions=allowed_extensions,
            enforce_resolution=enforce_resolution,
            required_px=logo_required_px,
            label="logo",
        )
    )
    validate_asset(
        AssetSpec(
            path=signature_path,
            allowed_extensions=allowed_extensions,
            enforce_resolution=enforce_resolution,
            required_px=signature_required_px,
            label="signature",
        )
    )
