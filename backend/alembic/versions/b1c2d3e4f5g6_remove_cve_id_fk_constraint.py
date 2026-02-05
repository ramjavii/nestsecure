"""Remove cve_id FK constraint from vulnerabilities

Revision ID: b1c2d3e4f5g6
Revises: 4c582262c53d
Create Date: 2026-02-05 19:00:00.000000

This migration removes the foreign key constraint on cve_id in the vulnerabilities
table. This allows storing CVE IDs that haven't been synced to cve_cache yet.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5g6'
down_revision: Union[str, None] = '4c582262c53d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove the FK constraint on cve_id."""
    # Drop the foreign key constraint
    op.drop_constraint(
        'fk_vulnerabilities_cve_id_cve_cache',
        'vulnerabilities',
        type_='foreignkey'
    )


def downgrade() -> None:
    """Re-add the FK constraint on cve_id."""
    op.create_foreign_key(
        'fk_vulnerabilities_cve_id_cve_cache',
        'vulnerabilities',
        'cve_cache',
        ['cve_id'],
        ['cve_id'],
        ondelete='SET NULL'
    )
