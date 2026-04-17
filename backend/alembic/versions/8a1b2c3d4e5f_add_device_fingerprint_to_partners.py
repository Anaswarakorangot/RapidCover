"""Add device_fingerprint to partners table

Revision ID: 8a1b2c3d4e5f
Revises:
Create Date: 2026-04-18 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8a1b2c3d4e5f'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('partners', sa.Column('device_fingerprint', sa.String(16), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('partners', 'device_fingerprint')
