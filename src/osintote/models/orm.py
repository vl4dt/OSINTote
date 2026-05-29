"""SQLAlchemy models for OSINTote.

All models use ``table=True`` so that ``configure_mappers()`` is triggered
at module level and resolves forward-referenced relationships correctly.
"""

from datetime import UTC, datetime
from enum import Enum as PydanticEnum
from typing import Any, TypeVar
from uuid import UUID, uuid4

import sqlmodel
from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator
from sqlalchemy import (
    JSON as SQLAlchemyJSON,  # noqa: N811
)
from sqlalchemy import (
    TIMESTAMP,
    Column,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SQLAlchemyEnum,
)
from sqlalchemy.orm import Mapped, configure_mappers
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel

# ── Base ────────────────────────────────────────────────────────────────────

T = TypeVar("T")


class ModelBase(SQLModel):
    """Base model with ``id`` and timestamps.

    Not a table itself — concrete models inherit and set ``table=True``.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: UUID | None = SQLField(default_factory=uuid4, primary_key=True)
    created_at: datetime = SQLField(
        default_factory=lambda: datetime.now(UTC),
    )
    updated_at: datetime = SQLField(
        default_factory=lambda: datetime.now(UTC),
    )


# ── Enums ───────────────────────────────────────────────────────────────────


class RecordType(str, PydanticEnum):  # noqa: UP042
    """OSINT record categories."""

    DNS = "dns"
    HTTP = "http"
    PORT = "port"
    WHOIS = "whois"
    SHODAN = "shodan"
    CENSYS = "censys"
    VIRUSTOTAL = "virustotal"
    VULNERABILITY = "vulnerability"
    GENERIC = "generic"


class TaskStatus(str, PydanticEnum):  # noqa: UP042
    """Task execution lifecycle."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class LogLevel(str, PydanticEnum):  # noqa: UP042
    """Log severity levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class WebhookEvent(str, PydanticEnum):  # noqa: UP042
    """Webhook event types."""

    ON_TASK_COMPLETE = "on_task_complete"
    ON_TASK_FAIL = "on_task_fail"
    ON_CRITICAL_FINDING = "on_critical_finding"
    ON_TARGET_ADD = "on_target_add"
    ON_TARGET_REMOVE = "on_target_remove"
    ON_TASK_START = "on_task_start"


class RelationshipType(str, PydanticEnum):  # noqa: UP042
    """Types of relationships between targets."""

    HOST_OF = "host_of"
    RESOLVES_TO = "resolves_to"
    PTR = "ptr"
    SUBDOMAIN = "subdomain"
    PARENT_DOMAIN = "parent_domain"
    IP_RANGE = "ip_range"
    CUSTOM = "custom"


# ── Models ──────────────────────────────────────────────────────────────────


class Target(ModelBase, table=True):
    """OSINT target — a domain, IP range, email, etc."""

    __tablename__ = "targets"
    __table_args__: Any = (UniqueConstraint("name", "type"),)

    name: str = SQLField(index=True, description="Primary identifier")
    type: str = SQLField(index=True, description="Target category")
    raw: str | None = SQLField(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Raw unprocessed target string",
    )
    tags: list[str] = SQLField(
        default_factory=list,
        sa_type=SQLAlchemyJSON(),
        description="User-assigned tags",
    )
    description: str | None = SQLField(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Human-readable notes",
    )

    # Relationships
    records: Mapped[list[Record]] = sqlmodel.Relationship(
        back_populates="target",
        cascade_delete=True,
    )
    tasks: Mapped[list[Task]] = sqlmodel.Relationship(
        back_populates="target",
        cascade_delete=True,
    )
    api_keys: Mapped[list[ApiKey]] = sqlmodel.Relationship(
        back_populates="target",
    )
    in_relations: Mapped[list[Relationship]] = sqlmodel.Relationship(
        back_populates="source",
        cascade_delete=True,
        sa_relationship_kwargs={"foreign_keys": "[Relationship.source_id]"},
    )
    out_relations: Mapped[list[Relationship]] = sqlmodel.Relationship(
        back_populates="target",
        cascade_delete=True,
        sa_relationship_kwargs={"foreign_keys": "[Relationship.target_id]"},
    )


class Record(ModelBase, table=True):
    """A single data record found during an OSINT pass."""

    __tablename__ = "records"
    __table_args__: Any = (UniqueConstraint("target_id", "type", "source"),)

    target_id: UUID = SQLField(foreign_key="targets.id")
    type: RecordType = SQLField(
        sa_column=SQLAlchemyEnum(RecordType, values_callable=lambda x: [e.value for e in x])
    )
    source: str = SQLField(index=True, description="Engine that produced this record")
    data: dict[str, Any] = SQLField(
        default={},
        sa_type=SQLAlchemyJSON(),
        description="Full response data",
    )
    metadata_: dict[str, Any] = SQLField(
        default_factory=dict,
        sa_type=SQLAlchemyJSON(),
        alias="metadata",
        description="Extra metadata (renamed from 'metadata' to avoid Python keyword conflict)",
    )
    confidence: float = SQLField(
        default=1.0,
        sa_column=Column(Integer, nullable=False, default=100),
        description="Confidence score 0-100",
    )

    # Relationships
    target: Mapped[Target] = sqlmodel.Relationship(back_populates="records")


class Task(ModelBase, table=True):
    """A backgrounded OSINT task linked to a target."""

    __tablename__ = "tasks"
    __table_args__: Any = (UniqueConstraint("name", "target_id"),)

    target_id: UUID | None = SQLField(
        default=None,
        foreign_key="targets.id",
        nullable=True,
    )
    name: str = SQLField(index=True, description="Task name")
    description: str | None = SQLField(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Task description",
    )
    status: TaskStatus = SQLField(
        default=TaskStatus.PENDING,
        sa_column=SQLAlchemyEnum(TaskStatus, values_callable=lambda x: [e.value for e in x]),
    )
    error_message: str | None = SQLField(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Error text if status == FAILED",
    )
    engine: str | None = SQLField(default=None, description="Engine identifier")
    recipe: str | None = SQLField(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Recipe identifier",
    )
    progress: float = SQLField(
        default=0.0,
        sa_column=Column(Integer, nullable=False, default=0),
        description="Progress percentage (0-100)",
    )
    result: dict[str, Any] = SQLField(
        default_factory=dict,
        sa_type=SQLAlchemyJSON(),
        description="Task result data",
    )
    started_at: datetime | None = SQLField(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True),
        description="When the task started",
    )
    completed_at: datetime | None = SQLField(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True),
        description="When the task completed",
    )

    # Relationships
    target: Mapped[Target] = sqlmodel.Relationship(back_populates="tasks")
    errors: Mapped[list[Error]] = sqlmodel.Relationship(
        back_populates="task",
        cascade_delete=True,
    )


class ApiKey(ModelBase, table=True):
    """API key for an external OSINT source."""

    __tablename__ = "api_keys"
    __table_args__: Any = (UniqueConstraint("source", "name"),)

    target_id: UUID | None = SQLField(
        default=None,
        foreign_key="targets.id",
        nullable=True,
    )
    name: str = SQLField(index=True, description="Key name")

    class Config:
        from_attributes = True

    source: str = SQLField(index=True, description="OSINT source (shodan, censys, etc.)")
    key: str | None = SQLField(
        default=None,
        sa_column=Column("key", Text, nullable=True),
        description="API key or credential",
    )

    def model_post_init(self, __context: Any) -> None:
        if isinstance(self.key, SecretStr):
            self.key = self.key.get_secret_value()  # type: ignore[assignment]

    encrypted: bool = SQLField(default=True, description="Whether the key is encrypted")
    fallback: bool = SQLField(default=False, description="Fallback key")
    primary: bool = SQLField(default=False, description="Primary key for this source")

    # Relationships
    target: Mapped[Target] = sqlmodel.Relationship(back_populates="api_keys")


class Setting(ModelBase, table=True):
    """Global / per-target configuration key-value store."""

    __tablename__ = "settings"
    __table_args__: Any = (UniqueConstraint("key"),)

    key: str = SQLField(index=True, unique=True, description="Setting key")
    value: dict[str, Any] = SQLField(
        default_factory=dict,
        sa_type=SQLAlchemyJSON(),
        description="Serialized setting value",
    )
    description: str | None = SQLField(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Human-readable description",
    )


class Relationship(ModelBase, table=True):
    """Link between two targets (e.g. domain → IP)."""

    __tablename__ = "relationships"
    __table_args__: Any = (UniqueConstraint("source_id", "target_id", "type"),)

    source_id: UUID = SQLField(foreign_key="targets.id")
    target_id: UUID = SQLField(foreign_key="targets.id")
    type: RelationshipType = SQLField(
        sa_column=SQLAlchemyEnum(RelationshipType, values_callable=lambda x: [e.value for e in x])
    )

    # Relationships (self-referential)
    source: Mapped[Target] = sqlmodel.Relationship(
        back_populates="in_relations",
        sa_relationship_kwargs={"foreign_keys": "[Relationship.source_id]"},
    )
    target: Mapped[Target] = sqlmodel.Relationship(
        back_populates="out_relations",
        sa_relationship_kwargs={"foreign_keys": "[Relationship.target_id]"},
    )


class Error(ModelBase, table=True):
    """Structured error / event log entry."""

    __tablename__ = "errors"

    severity: str = SQLField(
        index=True,
        description="Severity level (error, warning, etc.)",
    )
    logger: str = SQLField(index=True, description="Logger name")
    stage: str | None = SQLField(
        default=None,
        description="Stage that raised the error",
    )
    message: str = SQLField(
        sa_column=Column(Text, nullable=False),
        description="Error message",
    )
    meta: dict[str, Any] = SQLField(
        default_factory=dict,
        sa_type=SQLAlchemyJSON(),
        description="Additional error context",
    )
    task_id: UUID | None = SQLField(foreign_key="tasks.id")

    # Relationships
    task: Mapped[Task] = sqlmodel.Relationship(back_populates="errors")


class Webhook(ModelBase, table=True):
    """Webhook subscription for alerting."""

    __tablename__ = "webhooks"

    name: str = SQLField(index=True, description="Webhook name")
    url: str = SQLField(
        sa_column=Column(Text, nullable=False),
        description="Webhook endpoint URL",
    )
    events: list[str] = SQLField(
        default_factory=list,
        sa_type=SQLAlchemyJSON(),
        description="List of event types to subscribe to",
    )
    secret: str | None = SQLField(
        default=None,
        sa_column=Column("secret", Text, nullable=True),
        description="Signing secret for webhook validation",
    )

    def model_post_init(self, __context: Any) -> None:
        if isinstance(self.secret, SecretStr):
            self.secret = self.secret.get_secret_value()  # type: ignore[assignment]

    enabled: bool = SQLField(default=True, description="Whether the webhook is active")


class Log(ModelBase, table=True):
    """Structured log entries."""

    __tablename__ = "logs"

    level: LogLevel = SQLField(
        sa_column=SQLAlchemyEnum(LogLevel, values_callable=lambda x: [e.value for e in x])
    )
    logger: str = SQLField(index=True, description="Logger name")
    message: str = SQLField(sa_column=Column(Text, nullable=False), description="Log message")
    meta: dict[str, Any] = SQLField(
        default_factory=dict,
        sa_type=SQLAlchemyJSON(),
        description="Extra context",
    )
    task_id: UUID | None = SQLField(foreign_key="tasks.id")
    target_id: UUID | None = SQLField(foreign_key="targets.id")


# ── Pydantic Schemas ────────────────────────────────────────────────────────


class TargetCreate(SQLModel):
    """Schema for creating a target."""

    name: str = Field(min_length=1)
    type: str
    raw: str | None = None
    tags: list[str] = Field(default_factory=list)
    description: str | None = None


class TargetUpdate(SQLModel):
    """Schema for updating a target."""

    name: str | None = None
    type: str | None = None
    raw: str | None = None
    tags: list[str] | None = None
    description: str | None = None


class TargetRead(BaseModel):
    """Target read schema."""

    id: UUID | None = None
    name: str
    type: str
    raw: str | None = None
    tags: list[str] = Field(default_factory=list)
    description: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def _unset_unsaved_id(self) -> TargetRead:
        # Always expose id=None in read schemas — IDs are DB-managed
        self.id = None
        return self


class RecordCreate(SQLModel):
    """Schema for creating a record."""

    target_id: UUID
    type: RecordType
    source: str
    data: dict[str, Any] = {}
    confidence: float = 1.0


class TaskCreate(SQLModel):
    """Schema for creating a task."""

    target_id: UUID
    name: str
    description: str | None = None
    recipe: str | None = None


class ApiKeyCreate(SQLModel):
    """Schema for creating an API key."""

    target_id: UUID
    name: str
    source: str
    key: str
    primary: bool = False


class SettingCreate(SQLModel):
    """Schema for creating a setting."""

    key: str
    value: dict[str, Any]
    description: str | None = None


class RelationshipCreate(SQLModel):
    """Schema for creating a relationship."""

    source_id: UUID
    target_id: UUID
    type: RelationshipType


class ErrorCreate(SQLModel):
    """Schema for creating an error entry."""

    severity: str
    logger: str
    stage: str | None = None
    message: str
    meta: dict[str, Any] = {}
    task_id: UUID | None = None


class WebhookCreate(SQLModel):
    """Schema for creating a webhook."""

    name: str
    url: str
    events: list[str] = Field(default_factory=list)
    secret: str
    enabled: bool = True


# ── Update Schemas ─────────────────────────────────────────────────────────


class RecordUpdate(SQLModel):
    """Schema for updating a record."""

    type: RecordType | None = None
    source: str | None = None
    data: dict[str, Any] | None = None
    confidence: float | None = None


class TaskUpdate(SQLModel):
    """Schema for updating a task."""

    name: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    error_message: str | None = None
    recipe: str | None = None
    result: dict[str, Any] | None = None


class ApiKeyUpdate(SQLModel):
    """Schema for updating an API key."""

    name: str | None = None
    source: str | None = None
    key: str | None = None
    primary: bool | None = None


class SettingUpdate(SQLModel):
    """Schema for updating a setting."""

    key: str | None = None
    value: dict[str, Any] | None = None
    description: str | None = None


class RelationshipUpdate(SQLModel):
    """Schema for updating a relationship."""

    type: RelationshipType | None = None


class ErrorUpdate(SQLModel):
    """Schema for updating an error entry."""

    severity: str | None = None
    logger: str | None = None
    stage: str | None = None
    message: str | None = None
    meta: dict[str, Any] | None = None


class WebhookUpdate(SQLModel):
    """Schema for updating a webhook."""

    name: str | None = None
    url: str | None = None
    events: list[str] | None = None
    secret: str | None = None
    enabled: bool | None = None


class RecordRead(BaseModel):
    """Record read schema."""

    id: UUID | None = None
    target_id: UUID
    type: RecordType
    source: str
    data: dict[str, Any] = {}
    metadata_: dict[str, Any] = Field(default_factory=dict, alias="metadata")
    confidence: float = 1.0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class TaskRead(BaseModel):
    """Task read schema."""

    id: UUID | None = None
    target_id: UUID | None = None
    name: str
    description: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    error_message: str | None = None
    engine: str | None = None
    recipe: str | None = None
    progress: float = 0.0
    result: dict[str, Any] = {}
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class ApiKeyRead(BaseModel):
    """API key read schema (key is masked)."""

    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    target_id: UUID | None = None
    name: str
    source: str
    key: str = Field(default="****")
    encrypted: bool = True
    fallback: bool = False
    primary: bool = False
    model_config = ConfigDict(from_attributes=True)


class SettingRead(BaseModel):
    """Setting read schema."""

    id: UUID | None = None
    key: str
    value: dict[str, Any] = {}
    description: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class RelationshipRead(BaseModel):
    """Relationship read schema."""

    id: UUID | None = None
    source_id: UUID
    target_id: UUID
    type: RelationshipType
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class ErrorRead(BaseModel):
    """Error read schema."""

    id: UUID | None = None
    severity: str
    logger: str
    stage: str | None = None
    message: str
    meta: dict[str, Any] = {}
    task_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class WebhookRead(BaseModel):
    """Webhook read schema."""

    id: UUID | None = None
    name: str
    url: str
    events: list[str] = Field(default_factory=list)
    secret: str | None = None
    enabled: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


# ── Mapper Resolution ───────────────────────────────────────────────────────

# Resolve all forward-referenced relationships after all models are defined.
configure_mappers()


# ── Exports ─────────────────────────────────────────────────────────────────

__all__: list[str] = [  # noqa: RUF022
    # Models
    "Target",
    "Record",
    "Task",
    "ApiKey",
    "Setting",
    "Relationship",
    "Error",
    "Webhook",
    "Log",
    # Enums
    "RecordType",
    "TaskStatus",
    "LogLevel",
    "WebhookEvent",
    "RelationshipType",
    # Schemas
    "TargetCreate",
    "TargetUpdate",
    "TargetRead",
    "RecordCreate",
    "RecordRead",
    "TaskCreate",
    "TaskRead",
    "ApiKeyCreate",
    "ApiKeyRead",
    "SettingCreate",
    "SettingRead",
    "RelationshipCreate",
    "RelationshipRead",
    "ErrorCreate",
    "ErrorRead",
    "WebhookCreate",
    "WebhookRead",
    # Update schemas
    "TargetUpdate",
    "RecordUpdate",
    "TaskUpdate",
    "ApiKeyUpdate",
    "SettingUpdate",
    "RelationshipUpdate",
    "ErrorUpdate",
    "WebhookUpdate",
    # Base
    "ModelBase",
]
