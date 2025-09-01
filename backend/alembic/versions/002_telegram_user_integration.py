"""Telegram user integration

Revision ID: 002_telegram_user_integration
Revises: 001_initial_migration
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_telegram_user_integration'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Make username and email nullable for Telegram-only users
    op.alter_column('users', 'username',
                    existing_type=sa.VARCHAR(),
                    nullable=True)
    op.alter_column('users', 'email',
                    existing_type=sa.VARCHAR(),
                    nullable=True)
    op.alter_column('users', 'hashed_password',
                    existing_type=sa.VARCHAR(),
                    nullable=True)
    
    # Add new Telegram-specific columns
    op.add_column('users', sa.Column('telegram_first_name', sa.String(), nullable=True))
    op.add_column('users', sa.Column('telegram_last_name', sa.String(), nullable=True))
    op.add_column('users', sa.Column('telegram_language_code', sa.String(), nullable=True, default='en'))
    op.add_column('users', sa.Column('is_telegram_user', sa.Boolean(), nullable=True, default=False))
    op.add_column('users', sa.Column('digest_time', sa.String(), nullable=True, default='09:00'))
    op.add_column('users', sa.Column('min_importance_score', sa.Integer(), nullable=True, default=1))
    op.add_column('users', sa.Column('max_daily_notifications', sa.Integer(), nullable=True, default=10))
    op.add_column('users', sa.Column('timezone', sa.String(), nullable=True, default='UTC'))
    op.add_column('users', sa.Column('last_activity', sa.DateTime(timezone=True), nullable=True))
    
    # Add user categories table
    op.create_table('user_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('is_subscribed', sa.Boolean(), nullable=True, default=True),
        sa.Column('min_importance', sa.Integer(), nullable=True, default=1),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add user subscriptions table
    op.create_table('user_subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('keywords', sa.String(), nullable=True),
        sa.Column('min_importance', sa.Integer(), nullable=True, default=1),
        sa.Column('urgent_only', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['news_sources.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_user_categories_user_id'), 'user_categories', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_subscriptions_user_id'), 'user_subscriptions', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_subscriptions_source_id'), 'user_subscriptions', ['source_id'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index(op.f('ix_user_subscriptions_source_id'), table_name='user_subscriptions')
    op.drop_index(op.f('ix_user_subscriptions_user_id'), table_name='user_subscriptions')
    op.drop_index(op.f('ix_user_categories_user_id'), table_name='user_categories')
    
    # Drop tables
    op.drop_table('user_subscriptions')
    op.drop_table('user_categories')
    
    # Remove new columns
    op.drop_column('users', 'last_activity')
    op.drop_column('users', 'timezone')
    op.drop_column('users', 'max_daily_notifications')
    op.drop_column('users', 'min_importance_score')
    op.drop_column('users', 'digest_time')
    op.drop_column('users', 'is_telegram_user')
    op.drop_column('users', 'telegram_language_code')
    op.drop_column('users', 'telegram_last_name')
    op.drop_column('users', 'telegram_first_name')
    
    # Restore original nullable constraints
    op.alter_column('users', 'hashed_password',
                    existing_type=sa.VARCHAR(),
                    nullable=False)
    op.alter_column('users', 'email',
                    existing_type=sa.VARCHAR(),
                    nullable=False)
    op.alter_column('users', 'username',
                    existing_type=sa.VARCHAR(),
                    nullable=False)