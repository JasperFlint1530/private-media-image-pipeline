from pathlib import Path

from media_pipeline.image_jobs import AssetStore, ImageJobProcessor, ImageJobRequest


class RecordingGenerator:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate(self, *, asset_id: str, prompt: str) -> bytes:
        self.calls.append(asset_id)
        return b"stable-png-content"


def test_retry_reuses_asset_identity_and_replaces_one_private_file(tmp_path: Path) -> None:
    generator = RecordingGenerator()
    jobs = ImageJobProcessor(generator, AssetStore(tmp_path))
    request = ImageJobRequest(asset_id="patient-handout-42", prompt="A neutral hydration diagram")

    first = jobs.process(request)
    second = jobs.process(request)

    assert first == second
    assert first.state == "ready"
    assert first.delivery_path == "/assets/patient-handout-42"
    assert generator.calls == ["patient-handout-42", "patient-handout-42"]
    assert [path.name for path in tmp_path.iterdir()] == ["patient-handout-42.png"]
    assert (tmp_path / "patient-handout-42.png").stat().st_mode & 0o777 == 0o600
