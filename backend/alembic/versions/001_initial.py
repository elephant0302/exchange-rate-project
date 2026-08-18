"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-08-18

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "indicators",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("unit", sa.String(length=64), nullable=False),
        sa.Column("unit_label", sa.String(length=128), nullable=False),
        sa.Column("frequency", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("extra", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_indicators_code", "indicators", ["code"], unique=True)
    op.create_index("ix_indicators_category", "indicators", ["category"])

    op.create_table(
        "observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("indicator_id", sa.Integer(), sa.ForeignKey("indicators.id"), nullable=False),
        sa.Column("observed_at", sa.Date(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("is_mock", sa.Boolean(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("indicator_id", "observed_at", name="uq_observation_indicator_date"),
    )
    op.create_index("ix_observations_indicator_id", "observations", ["indicator_id"])
    op.create_index("ix_observations_observed_at", "observations", ["observed_at"])

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("indicator_id", sa.Integer(), sa.ForeignKey("indicators.id"), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=False),
        sa.Column("normalized_url", sa.String(length=1024), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("direction", sa.String(length=32), nullable=False),
        sa.Column("importance", sa.String(length=16), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("keywords", sa.Text(), nullable=False),
        sa.Column("is_mock", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("normalized_url", name="uq_event_normalized_url"),
    )
    op.create_index("ix_events_indicator_id", "events", ["indicator_id"])
    op.create_index("ix_events_published_at", "events", ["published_at"])
    op.create_index("ix_events_normalized_url", "events", ["normalized_url"])

    op.create_table(
        "forecasts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("indicator_id", sa.Integer(), sa.ForeignKey("indicators.id"), nullable=False),
        sa.Column("target_at", sa.Date(), nullable=False),
        sa.Column("predicted_value", sa.Float(), nullable=False),
        sa.Column("lower_bound", sa.Float(), nullable=False),
        sa.Column("upper_bound", sa.Float(), nullable=False),
        sa.Column("confidence_level", sa.Float(), nullable=False),
        sa.Column("model_name", sa.String(length=64), nullable=False),
        sa.Column("trained_from", sa.Date(), nullable=False),
        sa.Column("trained_to", sa.Date(), nullable=False),
        sa.Column("mae", sa.Float(), nullable=True),
        sa.Column("rmse", sa.Float(), nullable=True),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("is_mock", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "indicator_id",
            "target_at",
            "created_at",
            name="uq_forecast_indicator_target_created",
        ),
    )
    op.create_index("ix_forecasts_indicator_id", "forecasts", ["indicator_id"])
    op.create_index("ix_forecasts_target_at", "forecasts", ["target_at"])
    op.create_index("ix_forecasts_created_at", "forecasts", ["created_at"])

    op.create_table(
        "collection_statuses",
        sa.Column("job_name", sa.String(length=64), primary_key=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_mock", sa.Boolean(), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("collection_statuses")
    op.drop_table("forecasts")
    op.drop_table("events")
    op.drop_table("observations")
    op.drop_table("indicators")
