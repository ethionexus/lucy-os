"""Entry point for the Lucy OS offline semantic indexer systemd user service.

Starts the background SemanticIndexer and keeps it running until terminated.
"""
import logging
import signal
import sys
import time

from .search import SemanticIndexer


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s lucy-indexer %(levelname)s %(message)s",
    )
    log = logging.getLogger("lucy.indexer")

    indexer = SemanticIndexer()

    def _shutdown(signum, _frame):
        log.info("received signal %s, stopping indexer", signum)
        indexer.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    log.info("starting semantic indexer (backend=%s)", indexer.store.backend)
    indexer.start(background=True)
    while True:
        time.sleep(60)
        if isinstance(indexer.embedder, object):
            try:
                indexer.embedder.maybe_unload()  # type: ignore[attr-defined]
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
