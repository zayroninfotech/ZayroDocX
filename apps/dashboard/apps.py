import threading
import time
import os
from pathlib import Path
from django.apps import AppConfig

_OUTPUT_MAX_AGE = 3600   # delete output files older than 1 hour
_CLEANUP_INTERVAL = 600  # run cleanup every 10 minutes


def _output_cleanup_loop(dirs: list):
    while True:
        try:
            cutoff = time.time() - _OUTPUT_MAX_AGE
            for d in dirs:
                if not d.exists():
                    continue
                for f in d.iterdir():
                    if f.is_file() and f.stat().st_mtime < cutoff:
                        try:
                            f.unlink()
                        except OSError:
                            pass
        except Exception:
            pass
        time.sleep(_CLEANUP_INTERVAL)


class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.dashboard'
    label = 'dashboard'

    def ready(self):
        import apps.dashboard.signals  # noqa: F401 — registers signal handlers

        from django.conf import settings
        output_dir = getattr(settings, 'OUTPUT_DIR', None)
        if output_dir and os.environ.get('RUN_MAIN') == 'true':
            dirs = [Path(output_dir)]
            tmp_cs = getattr(settings, 'TMP_CS_DIR', None)
            if tmp_cs:
                dirs.append(Path(tmp_cs))
            t = threading.Thread(target=_output_cleanup_loop, args=(dirs,), daemon=True)
            t.start()
