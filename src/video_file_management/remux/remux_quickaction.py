import argparse
import subprocess
from pathlib import Path
from typing import Optional

from video_file_management.remux.remux2mp4 import (
    Remux2Mp4Config,
    Remux2Mp4Service,
    RemuxStatus,
)

TITLE = "Remux to MP4"
LOG_DIR = Path.home() / "Library" / "Logs" / "video_file_management"
LOG_FILE = LOG_DIR / "remux-to-mp4.log"


def _notify(message: str) -> None:
    try:
        escaped_message = message.replace('"', '\\"')
        # subprocess.run(
        #     [
        #         "/usr/bin/osascript",
        #         "-e",
        #         f'display notification "{escaped_message}" with title "{TITLE}"',
        #     ],
        #     check=False,
        #     capture_output=True,
        # )
    except Exception:
        return


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="remux-to-mp4",
        description="Remux compatible files into MP4 (stream copy only).",
    )
    parser.add_argument("files", nargs="+", help="Files to remux")
    args = parser.parse_args(argv)

    service = Remux2Mp4Service()

    for raw in args.files:
        path = Path(raw)
        config = Remux2Mp4Config(
            input_path=path,
            log_file=LOG_FILE,
            verbose=False,
        )
        try:
            results = service.run(config)
            for res in results:
                if res.status == RemuxStatus.CONVERTED:
                    print(f"Success: {res.message}")
                    _notify(f"Success: {res.message}")
                elif res.status == RemuxStatus.SKIPPED:
                    print(f"Skipped: {res.output_path.name}")
                    _notify(f"Skipped: {res.output_path.name}")
                elif res.status == RemuxStatus.FAILED:
                    print(f"Failed: {res.message}")
                    _notify(f"Failed: {res.message}")
                elif res.status == RemuxStatus.INCOMPATIBLE:
                    print(f"Incompatible: {res.message}")
                    _notify(f"Incompatible: {res.message}")
        except Exception as e:
            _notify(f"Error processing {path.name}: {e}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
