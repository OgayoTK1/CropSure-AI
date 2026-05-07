
from __future__ import annotations

from pathlib import Path


def _load_repo_dotenv() -> None:
	"""Best-effort loading of `cropsure-platform-new/.env`.

	Keeps local secrets out of source control while allowing the service to run
	from any working directory.
	"""

	try:
		from dotenv import load_dotenv
	except Exception:
		return

	repo_root = Path(__file__).resolve().parents[2]
	env_path = repo_root / ".env"
	if env_path.exists():
		load_dotenv(dotenv_path=env_path, override=False)


_load_repo_dotenv()

