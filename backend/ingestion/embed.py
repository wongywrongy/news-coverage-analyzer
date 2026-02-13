"""Embedding module for ClearSignal ingestion pipeline.

Generates 384-dimensional vector embeddings for articles using either
the OpenAI API (``text-embedding-3-small``) or a local
sentence-transformers model (``all-MiniLM-L6-v2``).

Both modes produce normalised ``list[float]`` of length 384, suitable
for cosine-similarity clustering and pgvector storage.
"""

from __future__ import annotations

import logging
import math
import time
from typing import TYPE_CHECKING

from config.settings import settings
from constants import EMBEDDING_BATCH_SIZE, EMBEDDING_DIMENSIONS
from models.schemas import Article

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_OPENAI_MODEL = settings.embedding_model
_OPENAI_DIMENSIONS = EMBEDDING_DIMENSIONS
_OPENAI_BATCH_SIZE = EMBEDDING_BATCH_SIZE
_OPENAI_MAX_RETRIES = 3
_OPENAI_BASE_DELAY = 1.0  # seconds

_LOCAL_MODEL_NAME = "all-MiniLM-L6-v2"

# Lazy-loaded sentence-transformers model (module-level cache).
_local_model = None


# ---------------------------------------------------------------------------
# Text preparation
# ---------------------------------------------------------------------------

def _prepare_text(article: Article) -> str:
    """Build the text string sent to the embedding model.

    Format: ``"{title}. {description[:200]}"``.  Truncating the
    description keeps token usage predictable while preserving the
    most informative content.
    """
    desc = (article.description or "")[:200]
    title = article.title or ""
    if desc:
        return f"{title}. {desc}"
    return title


# ---------------------------------------------------------------------------
# OpenAI embeddings
# ---------------------------------------------------------------------------

def _embed_openai(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts via the OpenAI API.

    Uses ``text-embedding-3-small`` with ``dimensions=384``.  Texts are
    sent in batches of 100 with exponential-backoff retry on HTTP 429.

    Args:
        texts: Non-empty strings to embed.

    Returns:
        A list of embedding vectors (each ``list[float]`` of length 384),
        positionally matching *texts*.  Failed texts get an empty list.
    """
    import openai  # deferred so the module loads without openai installed

    client = openai.OpenAI(api_key=settings.openai_api_key)
    all_embeddings: list[list[float]] = []

    for batch_start in range(0, len(texts), _OPENAI_BATCH_SIZE):
        batch = texts[batch_start : batch_start + _OPENAI_BATCH_SIZE]
        embedding_batch = _openai_batch_with_retry(client, batch)
        all_embeddings.extend(embedding_batch)

    return all_embeddings


def _openai_batch_with_retry(
    client: object,
    batch: list[str],
) -> list[list[float]]:
    """Send a single batch to OpenAI with exponential-backoff retry.

    Returns a list of embeddings matching *batch* length.  On total
    failure, returns empty lists so the pipeline can continue.
    """
    import openai

    delay = _OPENAI_BASE_DELAY
    for attempt in range(1, _OPENAI_MAX_RETRIES + 1):
        try:
            response = client.embeddings.create(  # type: ignore[union-attr]
                model=_OPENAI_MODEL,
                input=batch,
                dimensions=_OPENAI_DIMENSIONS,
            )
            # Response items are sorted by index
            sorted_data = sorted(response.data, key=lambda d: d.index)
            return [item.embedding for item in sorted_data]

        except openai.RateLimitError:
            if attempt < _OPENAI_MAX_RETRIES:
                logger.warning(
                    "OpenAI 429 — retrying in %.1fs (attempt %d/%d)",
                    delay, attempt, _OPENAI_MAX_RETRIES,
                )
                time.sleep(delay)
                delay *= 2
            else:
                logger.error(
                    "OpenAI 429 — exhausted %d retries", _OPENAI_MAX_RETRIES,
                )

        except openai.APIError as exc:
            logger.error("OpenAI API error: %s", exc)
            break

        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected OpenAI error: %s", exc)
            break

    # Total failure for this batch
    return [[] for _ in batch]


# ---------------------------------------------------------------------------
# Local embeddings (sentence-transformers)
# ---------------------------------------------------------------------------

def _get_local_model():  # type: ignore[no-untyped-def]
    """Lazy-load the sentence-transformers model (cached at module level)."""
    global _local_model  # noqa: PLW0603
    if _local_model is None:
        from sentence_transformers import SentenceTransformer

        logger.info("Loading local embedding model: %s", _LOCAL_MODEL_NAME)
        _local_model = SentenceTransformer(_LOCAL_MODEL_NAME)
    return _local_model


def _l2_normalize(vec: list[float]) -> list[float]:
    """Normalize a vector to unit length (L2 norm)."""
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        return vec
    return [x / norm for x in vec]


def _embed_local(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts using a local sentence-transformers model.

    Uses ``all-MiniLM-L6-v2`` which natively produces 384-dim vectors.
    Embeddings are L2-normalised for cosine-similarity compatibility.

    Args:
        texts: Non-empty strings to embed.

    Returns:
        A list of embedding vectors, positionally matching *texts*.
        Failed texts get an empty list.
    """
    try:
        model = _get_local_model()
        # encode() returns a numpy ndarray of shape (n, 384)
        raw = model.encode(texts, show_progress_bar=False)

        embeddings: list[list[float]] = []
        for row in raw:
            vec = row.tolist()
            embeddings.append(_l2_normalize(vec))
        return embeddings

    except Exception as exc:  # noqa: BLE001
        logger.error("Local embedding failed: %s", exc)
        return [[] for _ in texts]


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def embed_articles(
    articles: list[Article],
    mode: str | None = None,
) -> list[Article]:
    """Generate embeddings for a batch of articles.

    Each article's ``embedding`` field is populated in-place.  Articles
    that fail to embed are left with an empty list and a warning is
    logged.

    Args:
        articles: Normalised and deduplicated articles.
        mode: ``"openai"`` or ``"local"``.  Defaults to the value of
            ``settings.embedding_mode``.

    Returns:
        The same list of articles with ``embedding`` fields populated.
    """
    if not articles:
        return articles

    effective_mode = mode or settings.embedding_mode
    logger.info(
        "Embedding %d articles (mode=%s)", len(articles), effective_mode,
    )

    texts = [_prepare_text(art) for art in articles]

    if effective_mode == "openai":
        embeddings = _embed_openai(texts)
    elif effective_mode == "local":
        embeddings = _embed_local(texts)
    else:
        logger.error("Unknown embedding mode %r — skipping", effective_mode)
        return articles

    success = 0
    failed = 0
    for article, emb in zip(articles, embeddings):
        if emb:
            article.embedding = emb
            success += 1
        else:
            logger.warning("Empty embedding for: %s", article.url)
            failed += 1

    logger.info(
        "Embedding complete: %d succeeded, %d failed", success, failed,
    )
    return articles


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if "backend" not in sys.path[0]:
        sys.path.insert(0, ".")

    fixtures = [
        Article(
            url="https://nytimes.com/climate-bill",
            title="Senate Passes Major Climate Bill",
            description="The Senate voted 52-48 on a landmark climate bill after a marathon debate.",
            source_name="nytimes.com",
            source_domain="nytimes.com",
        ),
        Article(
            url="https://foxnews.com/border-update",
            title="Border Crossings Hit Record High",
            description="Border agents report a surge in illegal crossings at the southern border.",
            source_name="foxnews.com",
            source_domain="foxnews.com",
        ),
        Article(
            url="https://apnews.com/economy-q1",
            title="US Economy Grows 3.1% in Q1",
            description="Growth exceeded analyst expectations, driven by consumer spending.",
            source_name="apnews.com",
            source_domain="apnews.com",
        ),
    ]

    # Detect available mode
    mode = settings.embedding_mode
    try:
        import openai  # noqa: F401
        if settings.openai_api_key and settings.openai_api_key != "placeholder":
            mode = "openai"
        else:
            raise ImportError
    except ImportError:
        try:
            import sentence_transformers  # noqa: F401
            mode = "local"
        except ImportError:
            print("Neither openai nor sentence-transformers installed.")
            print("Install one to run this demo:")
            print("  pip install openai")
            print("  pip install sentence-transformers")
            sys.exit(1)

    print(f"Using mode: {mode}")
    results = embed_articles(fixtures, mode=mode)

    print(f"\n{'='*60}")
    print(f"Embedded {len(results)} articles")
    print(f"{'='*60}")
    for art in results:
        dims = len(art.embedding)
        preview = art.embedding[:5] if art.embedding else []
        preview_str = ", ".join(f"{v:.4f}" for v in preview)
        print(f"  [{art.source_domain}] {art.title}")
        print(f"    dims={dims}  first_5=[{preview_str}]")
        print()
