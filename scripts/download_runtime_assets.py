"""Download and verify the public model/data bundle used by the Render API."""

from hashlib import sha256
from pathlib import Path, PurePosixPath
import tempfile
from urllib.request import Request, urlopen
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSET_URL = (
    "https://github.com/pranavr14/hoops-iq/releases/download/"
    "hoops-iq-runtime-v2/hoops-iq-runtime-v2.zip"
)
EXPECTED_SHA256 = "c88f7e95320953d08ece2d96b0eb4ceaf788c336b8c785b532caa2b307febb25"
EXPECTED_FILES = {
    "data/player_game_logs_2025_27.csv",
    "models/artifacts/points_model_v2.joblib",
    "models/artifacts/rebounds_model_v2.joblib",
    "models/artifacts/assists_model_v2.joblib",
    "models/artifacts/threes_model_v2.joblib",
}


def main() -> None:
    request = Request(ASSET_URL, headers={"User-Agent": "HoopsIQ-deploy"})
    with urlopen(request, timeout=60) as response:
        bundle = response.read()

    actual_sha256 = sha256(bundle).hexdigest()
    if actual_sha256 != EXPECTED_SHA256:
        raise SystemExit(
            "Runtime asset checksum mismatch; refusing to extract the bundle."
        )

    with tempfile.NamedTemporaryFile(suffix=".zip") as archive_file:
        archive_file.write(bundle)
        archive_file.flush()

        with zipfile.ZipFile(archive_file.name) as archive:
            names = set(archive.namelist())
            if names != EXPECTED_FILES:
                raise SystemExit(
                    "Runtime asset bundle contents do not match the expected files."
                )

            for name in names:
                path = PurePosixPath(name)
                if path.is_absolute() or ".." in path.parts:
                    raise SystemExit("Unsafe path in runtime asset bundle.")

            archive.extractall(PROJECT_ROOT)

    missing = [name for name in EXPECTED_FILES if not (PROJECT_ROOT / name).is_file()]
    if missing:
        raise SystemExit(f"Runtime asset extraction is incomplete: {missing}")

    print(f"Installed and verified {len(EXPECTED_FILES)} runtime asset files.")


if __name__ == "__main__":
    main()
