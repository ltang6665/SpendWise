"""Protect one-time email codes and cap failed verification attempts.

Revision ID: otp_codes_20261029
Revises: None
Create Date: 2026-10-29
"""

from alembic import op
import sqlalchemy as sa


revision = "otp_codes_20261029"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("user_details"):
        return

    columns = {column["name"] for column in inspector.get_columns("user_details")}
    if "VerificationCodeFailedAttempts" not in columns:
        op.add_column(
            "user_details",
            sa.Column("VerificationCodeFailedAttempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        )
    if "ResetTokenFailedAttempts" not in columns:
        op.add_column(
            "user_details",
            sa.Column("ResetTokenFailedAttempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        )

    # Stored codes were plaintext; force outstanding requests to get fresh, hashed codes.
    op.execute(sa.text(
        'UPDATE "user_details" '
        'SET "VerificationCode" = NULL, "VerificationCodeExpiry" = NULL, '
        '"VerificationCodeFailedAttempts" = 0, "ResetToken" = NULL, '
        '"ResetTokenExpiry" = NULL, "ResetTokenFailedAttempts" = 0'
    ))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("user_details"):
        return

    columns = {column["name"] for column in inspector.get_columns("user_details")}
    if "ResetTokenFailedAttempts" in columns:
        op.drop_column("user_details", "ResetTokenFailedAttempts")
    if "VerificationCodeFailedAttempts" in columns:
        op.drop_column("user_details", "VerificationCodeFailedAttempts")
