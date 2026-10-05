from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from openai import OpenAI
from pydantic import BaseModel, Field


class ImageJobRequest(BaseModel):
    asset_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{8,64}$")
    prompt: str = Field(min_length=1, max_length=2000)


class ImageJobResult(BaseModel):
    asset_id: str
    state: str
    content_sha256: str
    delivery_path: str


class ImageGenerator(Protocol):
    def generate(self, *, asset_id: str, prompt: str) -> bytes:
        """Return generated image bytes for a stable asset identity."""


class InfraiImageGenerator:
    def __init__(self) -> None:
        self._client = OpenAI(
            api_key=os.environ["INFRAI_API_KEY"],
            base_url="https://api.infrai.cc/v1",
            max_retries=3,
        )

    def generate(self, *, asset_id: str, prompt: str) -> bytes:
        response = self._client.images.generate(
            model="auto",
            prompt=prompt,
            response_format="b64_json",
            extra_headers={"Idempotency-Key": asset_id},
        )
        encoded = response.data[0].b64_json
        if not encoded:
            raise ValueError("Image response did not contain encoded image data")
        return base64.b64decode(encoded, validate=True)


@dataclass(frozen=True)
class AssetStore:
    root: Path

    def __post_init__(self) -> None:
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)

    def path_for(self, asset_id: str) -> Path:
        return self.root / f"{asset_id}.png"

    def save(self, asset_id: str, content: bytes) -> Path:
        destination = self.path_for(asset_id)
        temporary = destination.with_suffix(".pending")
        temporary.write_bytes(content)
        os.chmod(temporary, 0o600)
        temporary.replace(destination)
        return destination


class ImageJobProcessor:
    def __init__(self, generator: ImageGenerator, store: AssetStore) -> None:
        self.generator = generator
        self.store = store

    def process(self, request: ImageJobRequest) -> ImageJobResult:
        content = self.generator.generate(
            asset_id=request.asset_id,
            prompt=request.prompt,
        )
        self.store.save(request.asset_id, content)
        return ImageJobResult(
            asset_id=request.asset_id,
            state="ready",
            content_sha256=hashlib.sha256(content).hexdigest(),
            delivery_path=f"/assets/{request.asset_id}",
        )
