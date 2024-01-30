"""empty message

Revision ID: 0029_fix_email_from
Revises: 0028_fix_reg_template_history
Create Date: 2016-06-13 15:15:34.035984

"""

# revision identifiers, used by Alembic.
from sqlalchemy import text

revision = "0029_fix_email_from"
down_revision = "0028_fix_reg_template_history"

import sqlalchemy as sa
from alembic import op

service_id = "d6aa2c68-a2d9-4437-ab19-3ae8eb202553"


def upgrade():
    conn = op.get_bind()
    input_params = {"service_id": service_id}
    conn.execute(
        text("update services set email_from = 'testsender' where id = :service_id"),
        input_params,
    )
    conn.execute(
        text(
            "update services_history set email_from = 'testsender' where id = :service_id"
        ),
        input_params,
    )


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    pass
    ### end Alembic commands ###
