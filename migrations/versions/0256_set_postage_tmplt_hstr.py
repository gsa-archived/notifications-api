"""

Revision ID: 0256_set_postage_tmplt_hstr
Revises: 0254_folders_for_all
Create Date: 2019-02-05 14:51:30.808067

"""

import sqlalchemy as sa
from alembic import op

revision = "0256_set_postage_tmplt_hstr"
down_revision = "0254_folders_for_all"


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute(
        """UPDATE templates_history SET postage = services.postage
        FROM services WHERE template_type = 'letter' AND service_id = services.id"""
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute(
        "UPDATE templates_history SET postage = null WHERE template_type = 'letter'"
    )
    # ### end Alembic commands ###
