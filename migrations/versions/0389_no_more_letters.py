"""

Revision ID: 0389_no_more_letters
Revises: 0388_no_serv_letter_contact
Create Date: 2023-02-28 08:58:38.310095

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0389_no_more_letters"
down_revision = "0388_no_serv_letter_contact"


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index("ix_returned_letters_service_id", table_name="returned_letters")
    op.drop_table("returned_letters")
    op.drop_index(
        "ix_daily_sorted_letter_billing_day", table_name="daily_sorted_letter"
    )
    op.drop_index("ix_daily_sorted_letter_file_name", table_name="daily_sorted_letter")
    op.drop_table("daily_sorted_letter")
    op.drop_column("services", "volume_letter")
    op.drop_column("services_history", "volume_letter")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "services_history",
        sa.Column("volume_letter", sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "services",
        sa.Column("volume_letter", sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.create_table(
        "daily_sorted_letter",
        sa.Column("id", postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column("billing_day", sa.DATE(), autoincrement=False, nullable=False),
        sa.Column("unsorted_count", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column("sorted_count", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(
            "updated_at", postgresql.TIMESTAMP(), autoincrement=False, nullable=True
        ),
        sa.Column("file_name", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint("id", name="daily_sorted_letter_pkey"),
        sa.UniqueConstraint(
            "file_name", "billing_day", name="uix_file_name_billing_day"
        ),
    )
    op.create_index(
        "ix_daily_sorted_letter_file_name",
        "daily_sorted_letter",
        ["file_name"],
        unique=False,
    )
    op.create_index(
        "ix_daily_sorted_letter_billing_day",
        "daily_sorted_letter",
        ["billing_day"],
        unique=False,
    )
    op.create_table(
        "returned_letters",
        sa.Column("id", postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column("reported_at", sa.DATE(), autoincrement=False, nullable=False),
        sa.Column("service_id", postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column(
            "notification_id", postgresql.UUID(), autoincrement=False, nullable=False
        ),
        sa.Column(
            "created_at", postgresql.TIMESTAMP(), autoincrement=False, nullable=False
        ),
        sa.Column(
            "updated_at", postgresql.TIMESTAMP(), autoincrement=False, nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["service_id"], ["services.id"], name="returned_letters_service_id_fkey"
        ),
        sa.PrimaryKeyConstraint("id", name="returned_letters_pkey"),
        sa.UniqueConstraint(
            "notification_id", name="returned_letters_notification_id_key"
        ),
    )
    op.create_index(
        "ix_returned_letters_service_id",
        "returned_letters",
        ["service_id"],
        unique=False,
    )
    # ### end Alembic commands ###
