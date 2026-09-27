"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-27

Creates the restaurant and menu_item tables. Money is NUMERIC(10, 2), not a
float, and the columns that get filtered or sorted carry indexes.
"""
from alembic import op
import sqlalchemy as sa


revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'restaurant',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('cuisine', sa.String(length=80), nullable=False),
        sa.Column('address', sa.String(length=200), nullable=False),
        sa.Column('is_open', sa.Boolean(), nullable=False),
        sa.Column('rating', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_restaurant_cuisine', 'restaurant', ['cuisine'])
    op.create_index('ix_restaurant_deleted_at', 'restaurant', ['deleted_at'])

    op.create_table(
        'menu_item',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('restaurant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('available', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['restaurant_id'], ['restaurant.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_menu_item_restaurant_id', 'menu_item', ['restaurant_id'])


def downgrade():
    op.drop_index('ix_menu_item_restaurant_id', table_name='menu_item')
    op.drop_table('menu_item')
    op.drop_index('ix_restaurant_deleted_at', table_name='restaurant')
    op.drop_index('ix_restaurant_cuisine', table_name='restaurant')
    op.drop_table('restaurant')
