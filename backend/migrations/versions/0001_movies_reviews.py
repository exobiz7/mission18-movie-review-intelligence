"""Create movies and reviews schema with FK cascade and positive-probability semantics.

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "movies",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("release_date", sa.Date(), nullable=False),
        sa.Column("director", sa.String(120), nullable=False),
        sa.Column("genre", sa.String(80), nullable=False),
        sa.Column("poster_url", sa.String(2048), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True, nullable=False),
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column("author", sa.String(80), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sentiment_label", sa.String(8), nullable=False),
        sa.Column("sentiment_score", sa.Float(), nullable=False),
        sa.Column("sentiment_confidence", sa.Float(), nullable=False),
        sa.Column("model_name", sa.String(255), nullable=False),
        sa.Column("model_revision", sa.String(80), nullable=False),
        sa.Column("inference_latency_ms", sa.Integer(), nullable=False),
        sa.Column("inferred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["movie_id"], ["movies.id"], name="fk_reviews_movie_id_movies", ondelete="CASCADE"
        ),
        sa.CheckConstraint(
            "sentiment_label IN ('positive','negative')", name="ck_reviews_sentiment_label"
        ),
        sa.CheckConstraint(
            "sentiment_score >= 0 AND sentiment_score <= 1", name="ck_reviews_sentiment_score"
        ),
        sa.CheckConstraint(
            "sentiment_confidence >= 0.5 AND sentiment_confidence <= 1",
            name="ck_reviews_sentiment_confidence",
        ),
        sa.CheckConstraint("inference_latency_ms >= 0", name="ck_reviews_inference_latency"),
    )
    op.create_index("ix_reviews_movie_created_id", "reviews", ["movie_id", "created_at", "id"])
    op.create_index("ix_reviews_created_id", "reviews", ["created_at", "id"])


def downgrade() -> None:
    op.drop_index("ix_reviews_created_id", table_name="reviews")
    op.drop_index("ix_reviews_movie_created_id", table_name="reviews")
    op.drop_table("reviews")
    op.drop_table("movies")
