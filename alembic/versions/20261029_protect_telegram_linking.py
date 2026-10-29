"""Expire and rate-limit Telegram account-link codes.

Revision ID: telegram_link_20261029
Revises: otp_codes_20261029
Create Date: 2026-10-29
"""

from alembic import op
import sqlalchemy as sa


revision = "telegram_link_20261029"
down_revision = "otp_codes_20261029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("user_details"):
        columns = {column["name"] for column in inspector.get_columns("user_details")}
        if "TelegramLinkCodeExpiry" not in columns:
            op.add_column(
                "user_details",
                sa.Column("TelegramLinkCodeExpiry", sa.DateTime(timezone=True), nullable=True),
            )

        # Existing link codes were plaintext and had no expiry; require users to generate new ones.
        if "TelegramLinkCode" in columns:
            op.execute(sa.text(
                'UPDATE "user_details" '
                'SET "TelegramLinkCode" = NULL, "TelegramLinkCodeExpiry" = NULL'
            ))

    if not inspector.has_table("telegram_link_attempts"):
        op.create_table(
            "telegram_link_attempts",
            sa.Column("TelegramId", sa.BigInteger(), nullable=False),
            sa.Column("FailedAttempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("WindowStartedAt", sa.DateTime(timezone=True), nullable=True),
            sa.Column("LockedUntil", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("TelegramId"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("telegram_link_attempts"):
        op.drop_table("telegram_link_attempts")

    if inspector.has_table("user_details"):
        columns = {column["name"] for column in inspector.get_columns("user_details")}
        if "TelegramLinkCodeExpiry" in columns:
            op.drop_column("user_details", "TelegramLinkCodeExpiry")
