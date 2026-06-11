"""renombrar columnas a espanol

Revision ID: 6c4d923b3ae8
Revises: f1689f331973
Create Date: 2026-06-11 13:31:04.854911

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c4d923b3ae8'
down_revision: Union[str, None] = 'f1689f331973'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Renombrar columnas (rename conserva los datos, a diferencia de drop+add)
    op.alter_column('clientes', 'name', new_column_name='nombre')
    op.alter_column('tipos_de_trabajo', 'title', new_column_name='titulo')
    op.alter_column('tipos_de_trabajo', 'client_id', new_column_name='cliente_id')
    op.alter_column('funciones_del_trabajo', 'title', new_column_name='titulo')
    op.alter_column('funciones_del_trabajo', 'job_id', new_column_name='trabajo_id')
    op.alter_column('perfil_del_trabajador', 'name', new_column_name='nombre')
    op.alter_column('perfil_del_trabajador', 'job_id', new_column_name='trabajo_id')
    op.alter_column('habilidades', 'name', new_column_name='nombre')
    op.alter_column('habilidades', 'job_id', new_column_name='trabajo_id')

    # Renombrar indices para que coincidan con lo que SQLAlchemy genera (ix_<tabla>_<columna>)
    op.execute('ALTER INDEX ix_clientes_name RENAME TO ix_clientes_nombre')
    op.execute('ALTER INDEX ix_tipos_de_trabajo_title RENAME TO ix_tipos_de_trabajo_titulo')
    op.execute('ALTER INDEX ix_funciones_del_trabajo_title RENAME TO ix_funciones_del_trabajo_titulo')


def downgrade() -> None:
    op.execute('ALTER INDEX ix_funciones_del_trabajo_titulo RENAME TO ix_funciones_del_trabajo_title')
    op.execute('ALTER INDEX ix_tipos_de_trabajo_titulo RENAME TO ix_tipos_de_trabajo_title')
    op.execute('ALTER INDEX ix_clientes_nombre RENAME TO ix_clientes_name')

    op.alter_column('habilidades', 'trabajo_id', new_column_name='job_id')
    op.alter_column('habilidades', 'nombre', new_column_name='name')
    op.alter_column('perfil_del_trabajador', 'trabajo_id', new_column_name='job_id')
    op.alter_column('perfil_del_trabajador', 'nombre', new_column_name='name')
    op.alter_column('funciones_del_trabajo', 'trabajo_id', new_column_name='job_id')
    op.alter_column('funciones_del_trabajo', 'titulo', new_column_name='title')
    op.alter_column('tipos_de_trabajo', 'cliente_id', new_column_name='client_id')
    op.alter_column('tipos_de_trabajo', 'titulo', new_column_name='title')
    op.alter_column('clientes', 'nombre', new_column_name='name')
