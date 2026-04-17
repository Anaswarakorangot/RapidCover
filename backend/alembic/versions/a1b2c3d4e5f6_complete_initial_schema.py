"""Complete initial schema

Revision ID: a1b2c3d4e5f6
Revises: 8a1b2c3d4e5f
Create Date: 2026-04-18 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '8a1b2c3d4e5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - create all tables."""
    conn = op.get_bind()
    dialect = conn.dialect.name

    # Create ENUM types for PostgreSQL
    if dialect == 'postgresql':
        conn.execute(sa.text("""
            DO $$ BEGIN
                CREATE TYPE platform AS ENUM ('zepto', 'blinkit');
            EXCEPTION WHEN duplicate_object THEN null;
            END $$;
        """))
        conn.execute(sa.text("""
            DO $$ BEGIN
                CREATE TYPE language AS ENUM ('en', 'ta', 'kn', 'te', 'hi', 'mr', 'bn');
            EXCEPTION WHEN duplicate_object THEN null;
            END $$;
        """))
        conn.execute(sa.text("""
            DO $$ BEGIN
                CREATE TYPE policytier AS ENUM ('flex', 'standard', 'pro');
            EXCEPTION WHEN duplicate_object THEN null;
            END $$;
        """))
        conn.execute(sa.text("""
            DO $$ BEGIN
                CREATE TYPE policystatus AS ENUM ('active', 'grace_period', 'lapsed', 'cancelled');
            EXCEPTION WHEN duplicate_object THEN null;
            END $$;
        """))
        conn.execute(sa.text("""
            DO $$ BEGIN
                CREATE TYPE triggertype AS ENUM ('rain', 'heat', 'aqi', 'shutdown', 'closure');
            EXCEPTION WHEN duplicate_object THEN null;
            END $$;
        """))
        conn.execute(sa.text("""
            DO $$ BEGIN
                CREATE TYPE claimstatus AS ENUM ('pending', 'approved', 'rejected', 'paid');
            EXCEPTION WHEN duplicate_object THEN null;
            END $$;
        """))
        conn.execute(sa.text("""
            DO $$ BEGIN
                CREATE TYPE reassignmentstatus AS ENUM ('pending', 'approved', 'rejected');
            EXCEPTION WHEN duplicate_object THEN null;
            END $$;
        """))

    # 1. Create independent base tables

    # zones table
    if not conn.dialect.has_table(conn, 'zones'):
        op.create_table('zones',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('code', sa.String(20), nullable=False),
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('city', sa.String(50), nullable=False),
            sa.Column('polygon', sa.Text(), nullable=True),
            sa.Column('risk_score', sa.Float(), nullable=True),
            sa.Column('is_suspended', sa.Boolean(), nullable=True),
            sa.Column('density_band', sa.String(20), nullable=True),
            sa.Column('dark_store_lat', sa.Float(), nullable=True),
            sa.Column('dark_store_lng', sa.Float(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_zones_city'), 'zones', ['city'], unique=False)
        op.create_index(op.f('ix_zones_code'), 'zones', ['code'], unique=True)
        op.create_index(op.f('ix_zones_id'), 'zones', ['id'], unique=False)

    # admins table
    if not conn.dialect.has_table(conn, 'admins'):
        op.create_table('admins',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('email', sa.String(255), nullable=False),
            sa.Column('hashed_password', sa.String(255), nullable=False),
            sa.Column('full_name', sa.String(100), nullable=False),
            sa.Column('is_active', sa.Boolean(), server_default=sa.text('1'), nullable=False),
            sa.Column('is_superadmin', sa.Boolean(), server_default=sa.text('0'), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
            sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_admins_email'), 'admins', ['email'], unique=True)
        op.create_index(op.f('ix_admins_id'), 'admins', ['id'], unique=False)

    # system_settings table
    if not conn.dialect.has_table(conn, 'system_settings'):
        op.create_table('system_settings',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('key', sa.String(100), nullable=False),
            sa.Column('value', sa.Text(), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_system_settings_key'), 'system_settings', ['key'], unique=True)

    # 2. Create tables that depend on zones

    # partners table
    if not conn.dialect.has_table(conn, 'partners'):
        platform_type = sa.Enum('zepto', 'blinkit', name='platform', create_type=False) if dialect == 'postgresql' else sa.String()
        language_type = sa.Enum('en', 'ta', 'kn', 'te', 'hi', 'mr', 'bn', name='language', create_type=False) if dialect == 'postgresql' else sa.String()

        op.create_table('partners',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('upi_id', sa.String(), nullable=True),
            sa.Column('phone', sa.String(15), nullable=False),
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('aadhaar_hash', sa.String(64), nullable=True),
            sa.Column('platform', platform_type, nullable=False),
            sa.Column('partner_id', sa.String(50), nullable=True),
            sa.Column('zone_id', sa.Integer(), nullable=True),
            sa.Column('language_pref', language_type, nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=True),
            sa.Column('shift_days', sa.JSON(), nullable=True),
            sa.Column('shift_start', sa.String(10), nullable=True),
            sa.Column('shift_end', sa.String(10), nullable=True),
            sa.Column('zone_history', sa.JSON(), nullable=True),
            sa.Column('bank_name', sa.String(100), nullable=True),
            sa.Column('account_number', sa.String(30), nullable=True),
            sa.Column('ifsc_code', sa.String(20), nullable=True),
            sa.Column('device_fingerprint', sa.String(16), nullable=True),
            sa.Column('platform_engagement_days', sa.Integer(), nullable=True),
            sa.Column('engagement_start_date', sa.DateTime(timezone=True), nullable=True),
            sa.Column('ss_code_eligible', sa.Boolean(), nullable=True),
            sa.Column('kyc', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['zone_id'], ['zones.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_partner_zone_active'), 'partners', ['zone_id', 'is_active'], unique=False)
        op.create_index(op.f('ix_partner_platform_active'), 'partners', ['platform', 'is_active'], unique=False)
        op.create_index(op.f('ix_partners_id'), 'partners', ['id'], unique=False)
        op.create_index(op.f('ix_partners_partner_id'), 'partners', ['partner_id'], unique=False)
        op.create_index(op.f('ix_partners_phone'), 'partners', ['phone'], unique=True)
        op.create_index(op.f('ix_partners_platform'), 'partners', ['platform'], unique=False)
        op.create_index(op.f('ix_partners_zone_id'), 'partners', ['zone_id'], unique=False)

    # zone_risk_profiles table
    if not conn.dialect.has_table(conn, 'zone_risk_profiles'):
        op.create_table('zone_risk_profiles',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('zone_id', sa.Integer(), nullable=False),
            sa.Column('risk_score', sa.Float(), nullable=False),
            sa.Column('features_json', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
            sa.ForeignKeyConstraint(['zone_id'], ['zones.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_zone_risk_profiles_id'), 'zone_risk_profiles', ['id'], unique=False)
        op.create_index(op.f('ix_zone_risk_profiles_zone_id'), 'zone_risk_profiles', ['zone_id'], unique=False)

    # trigger_events table
    if not conn.dialect.has_table(conn, 'trigger_events'):
        trigger_type = sa.Enum('rain', 'heat', 'aqi', 'shutdown', 'closure', name='triggertype', create_type=False) if dialect == 'postgresql' else sa.String()

        op.create_table('trigger_events',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('zone_id', sa.Integer(), nullable=False),
            sa.Column('trigger_type', trigger_type, nullable=False),
            sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('severity', sa.Integer(), nullable=True),
            sa.Column('source_data', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
            sa.ForeignKeyConstraint(['zone_id'], ['zones.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_trigger_events_id'), 'trigger_events', ['id'], unique=False)
        op.create_index(op.f('ix_trigger_events_zone_id'), 'trigger_events', ['zone_id'], unique=False)

    # sustained_events table
    if not conn.dialect.has_table(conn, 'sustained_events'):
        trigger_type = sa.Enum('rain', 'heat', 'aqi', 'shutdown', 'closure', name='triggertype', create_type=False) if dialect == 'postgresql' else sa.String()

        op.create_table('sustained_events',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('zone_id', sa.Integer(), nullable=False),
            sa.Column('trigger_type', trigger_type, nullable=False),
            sa.Column('consecutive_days', sa.Integer(), nullable=True),
            sa.Column('last_event_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('is_sustained', sa.Boolean(), nullable=True),
            sa.Column('history_json', sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(['zone_id'], ['zones.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_sustained_events_id'), 'sustained_events', ['id'], unique=False)
        op.create_index(op.f('ix_sustained_events_zone_id'), 'sustained_events', ['zone_id'], unique=False)

    # weather_observations table
    if not conn.dialect.has_table(conn, 'weather_observations'):
        op.create_table('weather_observations',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('zone_id', sa.Integer(), nullable=False),
            sa.Column('temp_celsius', sa.Float(), nullable=True),
            sa.Column('rainfall_mm_hr', sa.Float(), nullable=True),
            sa.Column('aqi', sa.Integer(), nullable=True),
            sa.Column('source', sa.String(), nullable=False),
            sa.Column('confidence', sa.Float(), nullable=True),
            sa.Column('api_provider', sa.String(), nullable=True),
            sa.Column('observed_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['zone_id'], ['zones.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_weather_observations_id'), 'weather_observations', ['id'], unique=False)
        op.create_index(op.f('ix_weather_observations_observed_at'), 'weather_observations', ['observed_at'], unique=False)
        op.create_index(op.f('ix_weather_observations_zone_id'), 'weather_observations', ['zone_id'], unique=False)

    # 3. Create tables that depend on partners

    # policies table
    if not conn.dialect.has_table(conn, 'policies'):
        tier_type = sa.Enum('flex', 'standard', 'pro', name='policytier', create_type=False) if dialect == 'postgresql' else sa.String()
        status_type = sa.Enum('active', 'grace_period', 'lapsed', 'cancelled', name='policystatus', create_type=False) if dialect == 'postgresql' else sa.String()

        op.create_table('policies',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('partner_id', sa.Integer(), nullable=False),
            sa.Column('tier', tier_type, nullable=False),
            sa.Column('weekly_premium', sa.Float(), nullable=False),
            sa.Column('max_daily_payout', sa.Float(), nullable=False),
            sa.Column('max_days_per_week', sa.Integer(), nullable=False),
            sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=True),
            sa.Column('auto_renew', sa.Boolean(), nullable=True),
            sa.Column('status', status_type, nullable=True),
            sa.Column('grace_ends_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('renewed_from_id', sa.Integer(), nullable=True),
            sa.Column('stripe_session_id', sa.String(), nullable=True),
            sa.Column('stripe_payment_intent', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['partner_id'], ['partners.id'], ),
            sa.ForeignKeyConstraint(['renewed_from_id'], ['policies.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_policy_partner_status'), 'policies', ['partner_id', 'status'], unique=False)
        op.create_index(op.f('ix_policy_expires_at'), 'policies', ['expires_at'], unique=False)
        op.create_index(op.f('ix_policy_tier_status'), 'policies', ['tier', 'status'], unique=False)
        op.create_index(op.f('ix_policies_id'), 'policies', ['id'], unique=False)
        op.create_index(op.f('ix_policies_partner_id'), 'policies', ['partner_id'], unique=False)
        op.create_index(op.f('ix_policies_status'), 'policies', ['status'], unique=False)
        op.create_index(op.f('ix_policies_stripe_session_id'), 'policies', ['stripe_session_id'], unique=True)
        op.create_index(op.f('ix_policies_tier'), 'policies', ['tier'], unique=False)

    # partner_devices table
    if not conn.dialect.has_table(conn, 'partner_devices'):
        op.create_table('partner_devices',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('partner_id', sa.Integer(), nullable=False),
            sa.Column('device_id', sa.String(), nullable=False),
            sa.Column('model', sa.String(), nullable=True),
            sa.Column('os_version', sa.String(), nullable=True),
            sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=True),
            sa.ForeignKeyConstraint(['partner_id'], ['partners.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_partner_devices_device_id'), 'partner_devices', ['device_id'], unique=False)
        op.create_index(op.f('ix_partner_devices_id'), 'partner_devices', ['id'], unique=False)
        op.create_index(op.f('ix_partner_devices_partner_id'), 'partner_devices', ['partner_id'], unique=False)

    # partner_gps_pings table
    if not conn.dialect.has_table(conn, 'partner_gps_pings'):
        op.create_table('partner_gps_pings',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('partner_id', sa.Integer(), nullable=False),
            sa.Column('lat', sa.Float(), nullable=False),
            sa.Column('lng', sa.Float(), nullable=False),
            sa.Column('source', sa.String(), nullable=True),
            sa.Column('device_id', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
            sa.ForeignKeyConstraint(['partner_id'], ['partners.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_partner_gps_pings_created_at'), 'partner_gps_pings', ['created_at'], unique=False)
        op.create_index(op.f('ix_partner_gps_pings_id'), 'partner_gps_pings', ['id'], unique=False)
        op.create_index(op.f('ix_partner_gps_pings_partner_id'), 'partner_gps_pings', ['partner_id'], unique=False)

    # push_subscriptions table
    if not conn.dialect.has_table(conn, 'push_subscriptions'):
        op.create_table('push_subscriptions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('partner_id', sa.Integer(), nullable=False),
            sa.Column('endpoint', sa.Text(), nullable=False),
            sa.Column('p256dh', sa.Text(), nullable=False),
            sa.Column('auth', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
            sa.ForeignKeyConstraint(['partner_id'], ['partners.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_push_subscriptions_id'), 'push_subscriptions', ['id'], unique=False)
        op.create_index(op.f('ix_push_subscriptions_partner_id'), 'push_subscriptions', ['partner_id'], unique=False)

    # zone_reassignments table
    if not conn.dialect.has_table(conn, 'zone_reassignments'):
        status_type = sa.Enum('pending', 'approved', 'rejected', name='reassignmentstatus', create_type=False) if dialect == 'postgresql' else sa.String()

        op.create_table('zone_reassignments',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('partner_id', sa.Integer(), nullable=False),
            sa.Column('from_zone_id', sa.Integer(), nullable=True),
            sa.Column('to_zone_id', sa.Integer(), nullable=False),
            sa.Column('reason', sa.Text(), nullable=True),
            sa.Column('status', status_type, nullable=True),
            sa.Column('requested_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
            sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('processed_by_admin_id', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['from_zone_id'], ['zones.id'], ),
            sa.ForeignKeyConstraint(['partner_id'], ['partners.id'], ),
            sa.ForeignKeyConstraint(['processed_by_admin_id'], ['admins.id'], ),
            sa.ForeignKeyConstraint(['to_zone_id'], ['zones.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_zone_reassignments_id'), 'zone_reassignments', ['id'], unique=False)
        op.create_index(op.f('ix_zone_reassignments_partner_id'), 'zone_reassignments', ['partner_id'], unique=False)
        op.create_index(op.f('ix_zone_reassignments_status'), 'zone_reassignments', ['status'], unique=False)

    # 4. Create tables that depend on policies

    # claims table
    if not conn.dialect.has_table(conn, 'claims'):
        status_type = sa.Enum('pending', 'approved', 'rejected', 'paid', name='claimstatus', create_type=False) if dialect == 'postgresql' else sa.String()

        op.create_table('claims',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('policy_id', sa.Integer(), nullable=False),
            sa.Column('trigger_event_id', sa.Integer(), nullable=False),
            sa.Column('amount', sa.Float(), nullable=False),
            sa.Column('status', status_type, nullable=True),
            sa.Column('fraud_score', sa.Float(), nullable=True),
            sa.Column('validation_data', sa.Text(), nullable=True),
            sa.Column('source_metadata', sa.Text(), nullable=True),
            sa.Column('upi_ref', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
            sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['policy_id'], ['policies.id'], ),
            sa.ForeignKeyConstraint(['trigger_event_id'], ['trigger_events.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_claims_id'), 'claims', ['id'], unique=False)
        op.create_index(op.f('ix_claims_policy_id'), 'claims', ['policy_id'], unique=False)
        op.create_index(op.f('ix_claims_status'), 'claims', ['status'], unique=False)
        op.create_index(op.f('ix_claim_policy_status'), 'claims', ['policy_id', 'status'], unique=False)
        op.create_index(op.f('ix_claim_created_at'), 'claims', ['created_at'], unique=False)
        op.create_index(op.f('ix_claim_trigger_status'), 'claims', ['trigger_event_id', 'status'], unique=False)

    # 5. Create other tables

    # drill_sessions table
    if not conn.dialect.has_table(conn, 'drill_sessions'):
        op.create_table('drill_sessions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('zone_id', sa.Integer(), nullable=True),
            sa.Column('session_date', sa.DateTime(timezone=True), nullable=False),
            sa.Column('drill_type', sa.String(50), nullable=False),
            sa.Column('participants_count', sa.Integer(), nullable=True),
            sa.Column('feedback_summary', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
            sa.ForeignKeyConstraint(['zone_id'], ['zones.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_drill_sessions_id'), 'drill_sessions', ['id'], unique=False)
        op.create_index(op.f('ix_drill_sessions_session_date'), 'drill_sessions', ['session_date'], unique=False)

    # active_event_trackers table
    if not conn.dialect.has_table(conn, 'active_event_trackers'):
        trigger_type = sa.Enum('rain', 'heat', 'aqi', 'shutdown', 'closure', name='triggertype', create_type=False) if dialect == 'postgresql' else sa.String()

        op.create_table('active_event_trackers',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('zone_id', sa.Integer(), nullable=False),
            sa.Column('trigger_type', trigger_type, nullable=False),
            sa.Column('last_event_date', sa.DateTime(timezone=True), nullable=False),
            sa.Column('consecutive_days', sa.Integer(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
            sa.ForeignKeyConstraint(['zone_id'], ['zones.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_active_event_trackers_id'), 'active_event_trackers', ['id'], unique=False)
        op.create_index(op.f('ix_active_event_trackers_zone_id'), 'active_event_trackers', ['zone_id'], unique=False)

    # fraud_predictions table
    if not conn.dialect.has_table(conn, 'fraud_predictions'):
        op.create_table('fraud_predictions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('claim_id', sa.Integer(), nullable=True),
            sa.Column('fraud_score', sa.Float(), nullable=False),
            sa.Column('model_version', sa.String(50), nullable=True),
            sa.Column('features_json', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
            sa.ForeignKeyConstraint(['claim_id'], ['claims.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_fraud_predictions_claim_id'), 'fraud_predictions', ['claim_id'], unique=False)
        op.create_index(op.f('ix_fraud_predictions_id'), 'fraud_predictions', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema - drop all tables."""
    conn = op.get_bind()

    # Drop tables in reverse order of creation
    tables_to_drop = [
        'fraud_predictions',
        'active_event_trackers',
        'drill_sessions',
        'claims',
        'zone_reassignments',
        'push_subscriptions',
        'partner_gps_pings',
        'partner_devices',
        'policies',
        'weather_observations',
        'sustained_events',
        'trigger_events',
        'zone_risk_profiles',
        'partners',
        'system_settings',
        'admins',
        'zones',
    ]

    for table_name in tables_to_drop:
        if conn.dialect.has_table(conn, table_name):
            op.drop_table(table_name)
