"""Download and verify the public model/data bundle used by the Render API."""

from hashlib import sha256
import csv
from pathlib import Path, PurePosixPath
import tempfile
from urllib.request import Request, urlopen
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSET_URL = (
    "https://github.com/pranavr14/hoops-iq/releases/download/"
    "hoops-iq-runtime-v2/hoops-iq-runtime-v2.zip"
)
EXPECTED_SHA256 = "5a6bf7913daf18e8f8c2054adbc25289d8094d7bccb00e8ff6ba95702cd3c785"
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

            # The game log is tracked in the deployment branch and refreshed
            # nightly. Keep that copy; the release copy is only a first-install
            # fallback. The trained models continue to come from the release.
            data_file = PROJECT_ROOT / "data/player_game_logs_2025_27.csv"
            for name in sorted(names):
                if name.startswith("models/artifacts/") or not data_file.is_file():
                    archive.extract(name, PROJECT_ROOT)

    missing = [name for name in EXPECTED_FILES if not (PROJECT_ROOT / name).is_file()]
    if missing:
        raise SystemExit(f"Runtime asset extraction is incomplete: {missing}")

    data_file = PROJECT_ROOT / "data/player_game_logs_2025_27.csv"
    with data_file.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        if not reader.fieldnames or not {"PLAYER_NAME", "GAME_DATE"}.issubset(
            reader.fieldnames
        ):
            raise SystemExit("Player game log is missing required columns.")
        dates = [row["GAME_DATE"] for row in reader if row.get("GAME_DATE")]
    if not dates:
        raise SystemExit("Player game log contains no game dates.")

    print(
        f"Installed models and verified player data through {max(dates)} "
        f"({len(EXPECTED_FILES)} expected bundle files)."
    )


if __name__ == "__main__":
    main()
