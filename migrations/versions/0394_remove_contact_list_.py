"""

Revision ID: 0394_remove_contact_list
Revises: 0393_remove_crown
Create Date: 2023-04-12 13:12:12.683257

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0394_remove_contact_list"
down_revision = "0393_remove_crown"


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint("jobs_contact_list_id_fkey", "jobs", type_="foreignkey")
    op.drop_index(
        "ix_service_contact_list_created_by_id", table_name="service_contact_list"
    )
    op.drop_index(
        "ix_service_contact_list_service_id", table_name="service_contact_list"
    )
    op.drop_table("service_contact_list")
    op.drop_column("jobs", "contact_list_id")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "jobs",
        sa.Column(
            "contact_list_id", postgresql.UUID(), autoincrement=False, nullable=True
        ),
    )
    op.create_table(
        "service_contact_list",
        sa.Column("id", postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column(
            "original_file_name", sa.VARCHAR(), autoincrement=False, nullable=False
        ),
        sa.Column("row_count", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(
            "template_type",
            postgresql.ENUM(
                "sms", "email", "letter", "broadcast", name="template_type"
            ),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column("service_id", postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column(
            "created_by_id", postgresql.UUID(), autoincrement=False, nullable=True
        ),
        sa.Column(
            "created_at", postgresql.TIMESTAMP(), autoincrement=False, nullable=False
        ),
        sa.Column(
            "updated_at", postgresql.TIMESTAMP(), autoincrement=False, nullable=True
        ),
        sa.Column(
            "archived",
            sa.BOOLEAN(),
            server_default=sa.text("false"),
            autoincrement=False,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name="service_contact_list_created_by_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["service_id"], ["services.id"], name="service_contact_list_service_id_fkey"
        ),
        sa.PrimaryKeyConstraint("id", name="service_contact_list_pkey"),
    )
    op.create_index(
        "ix_service_contact_list_service_id",
        "service_contact_list",
        ["service_id"],
        unique=False,
    )
    op.create_index(
        "ix_service_contact_list_created_by_id",
        "service_contact_list",
        ["created_by_id"],
        unique=False,
    )
    op.create_foreign_key(
        "jobs_contact_list_id_fkey",
        "jobs",
        "service_contact_list",
        ["contact_list_id"],
        ["id"],
    )
    # ### end Alembic commands ###
