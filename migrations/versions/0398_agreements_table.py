"""empty message

Revision ID: 0010_events_table
Revises: 0009_created_by_for_jobs
Create Date: 2016-04-26 13:08:42.892813

"""

# revision identifiers, used by Alembic.
revision = "0398_agreements_table"
down_revision = "0397_rename_organisation_2"

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "agreements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=3), nullable=False),
        sa.Column("partner_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=255), nullable=False),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=False),
        sa.Column("url", sa.String(length=255), nullable=False),
        sa.Column("budget_amount", sa.Float(), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("agreements")
    ### end Alembic commands ###
