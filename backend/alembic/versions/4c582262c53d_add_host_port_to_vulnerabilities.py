"""add_host_port_to_vulnerabilities

Revision ID: 4c582262c53d
Revises: 0680cdb4620c
Create Date: 2026-02-05 18:17:36.218330+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '4c582262c53d'
down_revision = '0680cdb4620c'
branch_labels = None
depends_on = None


def column_exists(table_name, column_name):
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # Add gvm columns to scans if they don't exist
    if not column_exists('scans', 'gvm_target_id'):
        op.add_column('scans', sa.Column('gvm_target_id', sa.String(255), nullable=True, comment='UUID del target en GVM'))
    if not column_exists('scans', 'gvm_task_id'):
        op.add_column('scans', sa.Column('gvm_task_id', sa.String(255), nullable=True, comment='UUID de la task en GVM'))
    if not column_exists('scans', 'gvm_report_id'):
        op.add_column('scans', sa.Column('gvm_report_id', sa.String(255), nullable=True, comment='UUID del report en GVM'))
    
    # Add host and port to vulnerabilities
    if not column_exists('vulnerabilities', 'host'):
        op.add_column('vulnerabilities', sa.Column('host', sa.String(length=255), nullable=True))
    if not column_exists('vulnerabilities', 'port'):
        op.add_column('vulnerabilities', sa.Column('port', sa.Integer(), nullable=True))


def downgrade() -> None:
    # Drop vulnerability columns
    if column_exists('vulnerabilities', 'port'):
        op.drop_column('vulnerabilities', 'port')
    if column_exists('vulnerabilities', 'host'):
        op.drop_column('vulnerabilities', 'host')
    
    # Drop gvm columns from scans
    if column_exists('scans', 'gvm_report_id'):
        op.drop_column('scans', 'gvm_report_id')
    if column_exists('scans', 'gvm_task_id'):
        op.drop_column('scans', 'gvm_task_id')
    if column_exists('scans', 'gvm_target_id'):
        op.drop_column('scans', 'gvm_target_id')
