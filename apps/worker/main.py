from datetime import datetime, timezone
from pathlib import Path

from waterinfohub.pipelines.ingest import run_ingest
from waterinfohub.pipelines.normalize import run_normalization


def main() -> None:
    now = datetime.now(timezone.utc).isoformat()
    project_root = Path(__file__).resolve().parents[2]
    ingest_stats = run_ingest(project_root / "configs")
    normalize_stats = run_normalization(project_root / "configs")
    print(
        f"worker run at {now} | fetched={ingest_stats.fetched} inserted={ingest_stats.inserted} "
        f"duplicated={ingest_stats.duplicated} failed={ingest_stats.failed} "
        f"| normalized_processed={normalize_stats.processed} normalized={normalize_stats.normalized} "
        f"skipped={normalize_stats.skipped} duplicate_events={normalize_stats.duplicated} "
        f"normalize_failed={normalize_stats.failed}"
    )


if __name__ == "__main__":
    main()
