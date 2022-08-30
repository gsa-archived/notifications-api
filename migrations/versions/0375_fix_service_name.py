"""empty message

Revision ID: 0375_fix_service_name
Revises: 0374_fix_reg_template_history
Create Date: 2022-08-29 11:04:15.888017

"""

# revision identifiers, used by Alembic.
from datetime import datetime

revision = '0375_fix_service_name'
down_revision = '0374_fix_reg_template_history'

from alembic import op
import sqlalchemy as sa

service_id = 'd6aa2c68-a2d9-4437-ab19-3ae8eb202553'
user_id= '6af522d0-2915-4e52-83a3-3690455a5fe6'

def upgrade():
    op.get_bind()
    
    # modify name of default service user in services
    table_name = 'services'
    col = 'name'
    val = 'US Notify'
    select_by_col = 'id'
    select_by_val = service_id
    op.execute(f"update {table_name} set {col}='{val}' where {select_by_col} = '{select_by_val}'")
    
    table_name = 'services_history'
    op.execute(f"update {table_name} set {col}='{val}' where {select_by_col} = '{select_by_val}'")
    

def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    pass
    ### end Alembic commands ###
