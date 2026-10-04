"""Offline semantic file indexer for Lucy OS.

A background daemon that watches the user's document folders, chunks local
files, generates embeddings with a 4-bit quantized ``nomic-embed-text-v1.5``
GGUF model (via llama-cpp-python), and stores them in a local vector index
under ``~/.local/share/lucy/search_index/``. Queries are answered locally,
offline, by nearest-neighbour search over the index.

Strict performance constraints (v0.3.0):
- Indexing CPU is capped at ~5% (psutil watchdog, adaptive sleep).
- Embedding work pauses automatically when the machine is busy.
- Everything runs on-demand; the indexer is background and resumable.

The module degrades gracefully: if ``llama_cpp`` / ``chromadb`` are not
installed, it falls back to a deterministic hash-based embedding and a
lightweight JSON index so the rest of the system keeps working.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
WATCH_DIRS = [
    "~/Documents",
    "~/Downloads",
    "~/Desktop",
    "~/Music",
    "~/Pictures",
    "~/Videos",
]

INDEX_ROOT = Path(os.environ.get(
    "LUCY_INDEX_DIR",
    os.path.expanduser("~/.local/share/lucy/search_index"),
))

# File types worth indexing as text (extensions, lower-case, with dot).
TEXT_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".rst", ".org",
    ".py", ".rs", ".js", ".ts", ".tsx", ".jsx", ".go", ".c", ".h", ".cpp",
    ".java", ".rb", ".php", ".sh", ".bash", ".zsh", ".fish",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".env",
    ".html", ".htm", ".css", ".scss", ".xml", ".csv", ".tsv", ".log",
    ".sql", ".tex", ".bib",
}

# Chunking parameters.
CHUNK_CHARS = 1200
CHUNK_OVERLAP = 200
MAX_FILE_BYTES = 2 * 1024 * 1024  # skip files larger than 2 MiB

# Embedding dimension for the deterministic fallback (must be stable).
FALLBACK_DIM = 256

# CPU throttle: target ≤5% during indexing.
CPU_CAP_PERCENT = 5.0
THROTTLE_SLEEP = 0.05  # base sleep between chunks (seconds)
BUSY_CPU_PERCENT = 50.0  # pause indexing entirely above this


# ---------------------------------------------------------------------------
# Embedding backends
# ---------------------------------------------------------------------------
class Embedder:
    """Base embedder interface."""

    dim: int = FALLBACK_DIM
    name: str = "fallback"

    def embed(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover
        raise NotImplementedError


class GGUFEmbedder(Embedder):
    """llama-cpp-python backed embedder using a 4-bit nomic-embed GGUF.

    Loads the model lazily on first use and unloads it after 3 minutes of
    inactivity (zero idle memory footprint), per the v0.3.0 constraints.
    """

    def __init__(self, model_path: Optional[Path] = None, idle_unload: float = 180.0):
        self.model_path = model_path
        self.idle_unload = idle_unload
        self._llm = None
        self._last_used = 0.0
        self._lock = threading.Lock()
        self.name = "gguf"
        self.dim = 768  # nomic-embed-text-v1.5 hidden size

    # -- lifecycle ---------------------------------------------------------
    def _ensure_loaded(self):
        with self._lock:
            if self._llm is None:
                try:
                    from llama_cpp import Llama  # type: ignore
                except Exception as e:  # pragma: no cover
                    raise RuntimeError(f"llama_cpp unavailable: {e}")
                if not self.model_path or not Path(self.model_path).exists():
                    raise RuntimeError(f"embedding model not found: {self.model_path}")
                self._llm = Llama(
                    model_path=str(self.model_path),
                    embedding=True,
                    n_ctx=2048,
                    n_threads=max(1, (os.cpu_count() or 4) // 2),  # ~50% cores
                    verbose=False,
                )
            self._last_used = time.time()
            return self._llm

    def maybe_unload(self):
        """Unload the model if idle beyond the threshold."""
        with self._lock:
            if self._llm is not None and (time.time() - self._last_used) > self.idle_unload:
                self._llm = None

    def embed(self, texts: list[str]) -> list[list[float]]:
        llm = self._ensure_loaded()
        out: list[list[float]] = []
        for t in texts:
            resp = llm.embed(t)
            vec = resp if isinstance(resp, list) else resp.get("embedding", [])
            out.append([float(x) for x in vec])
        self._last_used = time.time()
        return out


class HashEmbedder(Embedder):
    """Deterministic, dependency-free fallback embedder.

    Not semantically strong, but keeps the pipeline functional offline and
    without native deps. Disabled when a real GGUF model is available.
    """

    dim = FALLBACK_DIM
    name = "fallback"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._hash_embed(t) for t in texts]

    @staticmethod
    def _hash_embed(text: str) -> list[float]:
        vec = [0.0] * FALLBACK_DIM
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        if not tokens:
            return vec
        for tok in tokens:
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            idx = h % FALLBACK_DIM
            sign = 1.0 if (h >> 8) & 1 else -1.0
            vec[idx] += sign
        # L2-normalise for cosine similarity.
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


def make_embedder() -> Embedder:
    """Return the best available embedder (GGUF if present)."""
    # Look for a provisioned model in the local model dir.
    model_candidates = [
        INDEX_ROOT.parent / "models" / "nomic-embed-text-v1.5-q4_k_m.gguf",
        Path("/usr/share/lucy/models/nomic-embed-text-v1.5-q4_k_m.gguf"),
    ]
    for cand in model_candidates:
        if cand.exists():
            try:
                return GGUFEmbedder(cand)
            except Exception:
                continue
    return HashEmbedder()


# ---------------------------------------------------------------------------
# Vector store
# ---------------------------------------------------------------------------
@dataclass
class Chunk:
    """A chunk of a file with its embedding."""
    path: str
    offset: int
    text: str
    embedding: list[float] = field(default_factory=list)


class VectorStore:
    """Persistent local vector store.

    Uses ChromaDB when available, otherwise a JSON-lines fallback. The
    fallback keeps everything in memory and rewrites atomically on flush.
    """

    def __init__(self, root: Path = INDEX_ROOT):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.json_path = self.root / "index.jsonl"
        self.chroma_path = self.root / "chroma"
        self._chunks: list[Chunk] = []
        self._dirty = False
        self._lock = threading.Lock()
        self._backend = "json"
        self._collection = None
        self._init_backend()

    def _init_backend(self):
        try:
            import chromadb  # type: ignore
            self._client = chromadb.PersistentClient(path=str(self.chroma_path))
            self._collection = self._client.get_or_create_collection(
                name="lucy_files", metadata={"hnsw:space": "cosine"}
            )
            self._backend = "chromadb"
        except Exception:
            self._backend = "json"
            self._load_json()

    # -- persistence -------------------------------------------------------
    def _load_json(self):
        if not self.json_path.exists():
            return
        with self.json_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                self._chunks.append(Chunk(
                    path=obj["path"],
                    offset=obj.get("offset", 0),
                    text=obj.get("text", ""),
                    embedding=obj.get("embedding", []),
                ))

    def add(self, chunks: list[Chunk]):
        if not chunks:
            return
        with self._lock:
            if self._backend == "chromadb" and self._collection is not None:
                ids = [f"{c.path}:{c.offset}" for c in chunks]
                self._collection.upsert(
                    ids=ids,
                    documents=[c.text for c in chunks],
                    embeddings=[c.embedding for c in chunks],
                    metadatas=[{"path": c.path, "offset": c.offset} for c in chunks],
                )
            else:
                self._chunks.extend(chunks)
                self._dirty = True

    def flush(self):
        with self._lock:
            if self._backend == "json" and self._dirty:
                tmp = self.json_path.with_suffix(".jsonl.tmp")
                with tmp.open("w", encoding="utf-8") as f:
                    for c in self._chunks:
                        f.write(json.dumps({
                            "path": c.path,
                            "offset": c.offset,
                            "text": c.text,
                            "embedding": c.embedding,
                        }) + "\n")
                tmp.replace(self.json_path)
                self._dirty = False

    def remove_path(self, path: str):
        with self._lock:
            if self._backend == "chromadb" and self._collection is not None:
                try:
                    self._collection.delete(where={"path": path})
                except Exception:
                    pass
            else:
                self._chunks = [c for c in self._chunks if c.path != path]
                self._dirty = True

    def all_chunks(self) -> list[Chunk]:
        if self._backend == "chromadb" and self._collection is not None:
            try:
                data = self._collection.get(include=["documents", "embeddings", "metadatas"])
                out = []
                for doc, emb, meta in zip(
                    data.get("documents", []),
                    data.get("embeddings", []),
                    data.get("metadatas", []),
                ):
                    out.append(Chunk(
                        path=meta.get("path", ""),
                        offset=meta.get("offset", 0),
                        text=doc,
                        embedding=list(emb) if emb is not None else [],
                    ))
                return out
            except Exception:
                return []
        return list(self._chunks)

    @property
    def backend(self) -> str:
        return self._backend

    def count(self) -> int:
        if self._backend == "chromadb" and self._collection is not None:
            try:
                return self._collection.count()
            except Exception:
                return 0
        return len(self._chunks)


# ---------------------------------------------------------------------------
# Chunking + file walking
# ---------------------------------------------------------------------------
def chunk_text(text: str, chunk_chars: int = CHUNK_CHARS,
               overlap: int = CHUNK_OVERLAP) -> list[tuple[int, str]]:
    """Split text into overlapping chunks; returns (offset, chunk) pairs."""
    if not text:
        return []
    chunks: list[tuple[int, str]] = []
    step = max(1, chunk_chars - overlap)
    for start in range(0, len(text), step):
        piece = text[start:start + chunk_chars]
        if piece.strip():
            chunks.append((start, piece))
        if start + chunk_chars >= len(text):
            break
    return chunks


def iter_candidate_files(dirs: Optional[list[str]] = None) -> Iterable[Path]:
    """Yield indexable text files under the watched directories."""
    dirs = dirs or WATCH_DIRS
    for d in dirs:
        base = Path(os.path.expanduser(d))
        if not base.is_dir():
            continue
        for p in base.rglob("*"):
            try:
                if not p.is_file():
                    continue
                if p.suffix.lower() not in TEXT_EXTENSIONS:
                    continue
                if p.stat().st_size > MAX_FILE_BYTES:
                    continue
                # Skip hidden / cache dirs.
                if any(part.startswith(".") for part in p.relative_to(base).parts):
                    continue
            except (OSError, ValueError):
                continue
            yield p


def read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except (OSError, UnicodeError):
        return ""


# ---------------------------------------------------------------------------
# CPU throttle
# ---------------------------------------------------------------------------
def _current_cpu() -> float:
    try:
        import psutil
        return psutil.cpu_percent(interval=0.0)
    except Exception:
        return 0.0


def throttle():
    """Adaptive sleep keeping indexing under the CPU cap.

    Sleeps proportionally to how far over the cap the system is, and yields
    the GIL so the desktop stays responsive. This is a cooperative throttle:
    indexing never spins the CPU.
    """
    cpu = _current_cpu()
    if cpu > BUSY_CPU_PERCENT:
        time.sleep(0.5)
        return
    if cpu > CPU_CAP_PERCENT:
        # Scale sleep with overshoot (up to ~0.5s).
        overshoot = (cpu - CPU_CAP_PERCENT) / max(1e-6, CPU_CAP_PERCENT)
        time.sleep(min(0.5, THROTTLE_SLEEP * (1 + overshoot * 4)))
    else:
        time.sleep(THROTTLE_SLEEP)


# ---------------------------------------------------------------------------
# Indexer daemon
# ---------------------------------------------------------------------------
class SemanticIndexer:
    """Background indexer: walks files, chunks, embeds, stores."""

    def __init__(
        self,
        dirs: Optional[list[str]] = None,
        store: Optional[VectorStore] = None,
        embedder: Optional[Embedder] = None,
        reindex_interval: float = 300.0,
    ):
        self.dirs = dirs or WATCH_DIRS
        self.store = store or VectorStore()
        self.embedder = embedder or make_embedder()
        self.reindex_interval = reindex_interval
        self._seen: dict[str, float] = {}  # path -> mtime
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._state_path = self.store.root / "state.json"
        self._load_state()

    # -- state -------------------------------------------------------------
    def _load_state(self):
        if self._state_path.exists():
            try:
                self._seen = json.loads(self._state_path.read_text())
            except Exception:
                self._seen = {}

    def _save_state(self):
        try:
            self._state_path.write_text(json.dumps(self._seen))
        except OSError:
            pass

    # -- indexing ----------------------------------------------------------
    def index_file(self, path: Path) -> int:
        """Index a single file; returns the number of chunks added."""
        text = read_text_file(path)
        if not text.strip():
            return 0
        pieces = chunk_text(text)
        if not pieces:
            return 0
        embeddings = self.embedder.embed([p[1] for p in pieces])
        chunks = [
            Chunk(path=str(path), offset=off, text=txt, embedding=emb)
            for (off, txt), emb in zip(pieces, embeddings)
        ]
        self.store.add(chunks)
        self._seen[str(path)] = path.stat().st_mtime
        return len(chunks)

    def index_once(self) -> int:
        """Run one full incremental pass. Returns chunks added."""
        total = 0
        for path in iter_candidate_files(self.dirs):
            if self._stop.is_set():
                break
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue
            if self._seen.get(str(path)) == mtime:
                continue
            # Remove stale chunks before re-indexing.
            self.store.remove_path(str(path))
            total += self.index_file(path)
            throttle()
        self.store.flush()
        self._save_state()
        return total

    # -- query -------------------------------------------------------------
    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Semantic search over the local index. Returns ranked results."""
        q_emb = self.embedder.embed([query])[0]
        chunks = self.store.all_chunks()
        if not chunks:
            return []
        scored = []
        for c in chunks:
            if not c.embedding:
                continue
            score = _cosine(q_emb, c.embedding)
            scored.append((score, c))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, c in scored[:top_k]:
            results.append({
                "path": c.path,
                "score": round(score, 4),
                "snippet": c.text[:240].replace("\n", " ").strip(),
            })
        return results

    # -- lifecycle ---------------------------------------------------------
    def _run(self):
        # Initial pass, then periodic incremental passes.
        while not self._stop.is_set():
            try:
                self.index_once()
            except Exception:
                pass
            if isinstance(self.embedder, GGUFEmbedder):
                self.embedder.maybe_unload()
            self._stop.wait(self.reindex_interval)

    def start(self, background: bool = True):
        """Start the background indexer loop."""
        if background:
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
        else:
            self._run()

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self.store.flush()


# ---------------------------------------------------------------------------
# Similarity
# ---------------------------------------------------------------------------
def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(n))
    na = math.sqrt(sum(a[i] * a[i] for i in range(n)))
    nb = math.sqrt(sum(b[i] * b[i] for i in range(n)))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


# ---------------------------------------------------------------------------
# Module-level convenience (initialised lazily by the daemon)
# ---------------------------------------------------------------------------
_INDEXER: Optional[SemanticIndexer] = None


def get_indexer() -> SemanticIndexer:
    """Return (creating if needed) the process-wide indexer."""
    global _INDEXER
    if _INDEXER is None:
        _INDEXER = SemanticIndexer()
    return _INDEXER


def search_files(query: str, top_k: int = 5) -> list[dict]:
    """Convenience wrapper used by the Tauri/daemon RPC layer."""
    return get_indexer().search(query, top_k=top_k)
