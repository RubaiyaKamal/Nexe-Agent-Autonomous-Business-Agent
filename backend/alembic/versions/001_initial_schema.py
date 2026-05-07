"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None

# Enum definitions with create_type=False — created manually below with checkfirst
_goal_status = postgresql.ENUM(
    "received", "planning", "plan_ready", "approved", "executing",
    "completed", "cancelled", "failed", name="goal_status", create_type=False
)
_plan_status = postgresql.ENUM("draft", "approved", "cancelled", name="plan_status", create_type=False)
_task_type = postgresql.ENUM(
    "data_retrieval", "content_generation", "notification_dispatch", name="task_type", create_type=False
)
_complexity_level = postgresql.ENUM("low", "medium", "high", name="complexity_level", create_type=False)
_task_status = postgresql.ENUM(
    "queued", "running", "succeeded", "failed", "skipped", "retrying", name="task_status", create_type=False
)
_run_status = postgresql.ENUM(
    "pending", "running", "completed", "failed", "cancelled", "pending_clarification",
    name="run_status", create_type=False
)
_log_status = postgresql.ENUM(
    "queued", "running", "succeeded", "failed", "skipped", "retrying",
    "cancelled", "notification", "run_started", "run_completed", "run_failed", "run_cancelled",
    name="log_status", create_type=False
)


def _create_enums(bind) -> None:
    for name, values in [
        ("goal_status", ["received", "planning", "plan_ready", "approved", "executing", "completed", "cancelled", "failed"]),
        ("plan_status", ["draft", "approved", "cancelled"]),
        ("task_type", ["data_retrieval", "content_generation", "notification_dispatch"]),
        ("complexity_level", ["low", "medium", "high"]),
        ("task_status", ["queued", "running", "succeeded", "failed", "skipped", "retrying"]),
        ("run_status", ["pending", "running", "completed", "failed", "cancelled", "pending_clarification"]),
        ("log_status", ["queued", "running", "succeeded", "failed", "skipped", "retrying",
                        "cancelled", "notification", "run_started", "run_completed", "run_failed", "run_cancelled"]),
    ]:
        postgresql.ENUM(*values, name=name).create(bind, checkfirst=True)


def upgrade() -> None:
    bind = op.get_bind()
    _create_enums(bind)

    # users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("auto_execute", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )

    # goals
    op.create_table(
        "goals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("submitted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", _goal_status, nullable=False, server_default="received"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("char_length(text) <= 2000", name="ck_goal_text_length"),
    )

    # plans
    op.create_table(
        "plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("goal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("goals.id"), nullable=False, unique=True),
        sa.Column("status", _plan_status, nullable=False, server_default="draft"),
        sa.Column("task_count", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("task_count >= 1 AND task_count <= 20", name="ck_plan_task_count"),
    )

    # tasks
    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("plans.id"), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("task_type", _task_type, nullable=False),
        sa.Column("complexity", _complexity_level, nullable=False),
        sa.Column("status", _task_status, nullable=False, server_default="queued"),
        sa.Column("dependencies", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False, server_default="{}"),
        sa.Column("is_critical_path", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("order_index", sa.Integer, nullable=False),
        sa.Column("timeout_seconds", sa.Integer, nullable=False, server_default="60"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # execution_runs
    op.create_table(
        "execution_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("plans.id"), nullable=False),
        sa.Column("triggered_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", _run_status, nullable=False, server_default="pending"),
        sa.Column("auto_execute", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("tasks_total", sa.Integer, nullable=False, server_default="0"),
        sa.Column("tasks_succeeded", sa.Integer, nullable=False, server_default="0"),
        sa.Column("tasks_failed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("tasks_skipped", sa.Integer, nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_runs_one_active_per_plan",
        "execution_runs",
        ["plan_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'running')"),
    )

    # log_entries (append-only)
    op.create_table(
        "log_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("execution_runs.id"), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tasks.id"), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("status", _log_status, nullable=False),
        sa.Column("reasoning_summary", sa.Text, nullable=False),
        sa.Column("input_snapshot", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("output_snapshot", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("error_context", sa.Text, nullable=True),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_index("idx_log_run_timestamp", "log_entries", ["run_id", "timestamp"])
    op.create_index("idx_log_run_task", "log_entries", ["run_id", "task_id"])
    op.create_index("idx_log_status", "log_entries", ["status"])

    # reasoning_traces
    op.create_table(
        "reasoning_traces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("execution_runs.id"), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("step_index", sa.Integer, nullable=False),
        sa.Column("current_state", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("decision", sa.Text, nullable=False),
        sa.Column("rationale", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_trace_run_task_step", "reasoning_traces", ["run_id", "task_id", "step_index"])

    # app_writer role: INSERT-only on log_entries
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_writer') THEN
                CREATE ROLE app_writer;
            END IF;
        END
        $$;
    """)
    op.execute("GRANT INSERT ON log_entries TO app_writer;")
    op.execute("REVOKE UPDATE, DELETE ON log_entries FROM PUBLIC;")


def downgrade() -> None:
    op.drop_table("reasoning_traces")
    op.drop_index("idx_log_run_timestamp", table_name="log_entries")
    op.drop_index("idx_log_run_task", table_name="log_entries")
    op.drop_index("idx_log_status", table_name="log_entries")
    op.drop_table("log_entries")
    op.drop_index("idx_runs_one_active_per_plan", table_name="execution_runs")
    op.drop_table("execution_runs")
    op.drop_table("tasks")
    op.drop_table("plans")
    op.drop_table("goals")
    op.drop_table("users")
    for name in ["log_status", "run_status", "task_status", "complexity_level", "task_type", "plan_status", "goal_status"]:
        op.execute(f"DROP TYPE IF EXISTS {name}")
