SHARED CONTEXT FOR ALL CLEARSIGNAL AGENTS:

You are building a module for news-attention-tracker, a news platform
that makes media attention gaps visible. The backend is a Python 3.12
pipeline that runs locally, stores data in Supabase (Postgres + pgvector),
and uses OpenAI for embeddings and Claude for AI analysis.

PROJECT ROOT: news-attention-tracker/  (or clearsignal-backend/)

CONVENTIONS:
- Type hints on all function signatures
- Docstrings on all public functions and classes
- Use logging via: import logging; logger = logging.getLogger(__name__)
- No global state — receive dependencies as function parameters
- Handle errors gracefully — log and continue, never crash the pipeline
- Each file must be runnable standalone for testing:
  if __name__ == "__main__": block with demo/test code

DATABASE STATE:
- ~1152 articles with embeddings in Supabase
- ~106 active stories with article_count, source_count, centroids, topics
- Stories have articles assigned via articles.story_id FK

KEY DB FUNCTIONS AVAILABLE (from db/queries.py):
- get_active_stories() → list[dict]
- get_articles_for_story(story_id: int) → list[dict]
- update_story_scores(story_id: int, impact: float, attention: float)
- update_story_metadata(story_id: int, **kwargs)
- update_article_story(article_id: int, story_id: int)

KEY MODELS (from models/schemas.py):
- Story: {id, topic, category, impact_score, attention_score,
  article_count, source_count, centroid, is_active, first_seen,
  last_updated, status, sentiment_left, sentiment_center,
  sentiment_right, trend, peak_date, population_affected, ...}