"""

Revision ID: 0376_add_org_names
Revises: 0375_fix_service_name
Create Date: 2022-09-23 20:04:00.766980

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0376_add_org_names'
down_revision = '0375_fix_service_name'


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.get_bind()

    op.execute("INSERT INTO organisation_types VALUES ('state','f','250000'),('federal','f','250000');")
    

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###
