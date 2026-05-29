"""Models package — ORM models, Pydantic schemas, and database utilities.

Public API::

    from osintote.models import Target, Task, Record
    from osintote.models.database import AsyncSessionLocal, get_async_session
    from osintote.models.orm import TargetCreate, TaskStatus, RecordType

    # Create a target
    target = Target(name="example.com", type="domain")

    # Check task status enum values
    assert TaskStatus.PENDING.value == "pending"
"""

from osintote.models.database import (
    DATABASE_URL,
    AsyncSessionLocal,
    Base,
    auto_migrate,
    engine,
    get_async_session,
    init_db,
)
from osintote.models.orm import (
    ApiKey,
    ApiKeyCreate,
    ApiKeyRead,
    ApiKeyUpdate,
    Error,
    ErrorCreate,
    ErrorRead,
    ErrorUpdate,
    ModelBase,
    Record,
    RecordCreate,
    RecordRead,
    RecordType,
    RecordUpdate,
    Relationship,
    RelationshipCreate,
    RelationshipRead,
    RelationshipType,
    RelationshipUpdate,
    Setting,
    SettingCreate,
    SettingRead,
    SettingUpdate,
    # Models
    Target,
    # Create schemas
    TargetCreate,
    # Read schemas
    TargetRead,
    # Update schemas
    TargetUpdate,
    Task,
    TaskCreate,
    TaskRead,
    # Enums
    TaskStatus,
    TaskUpdate,
    Webhook,
    WebhookCreate,
    WebhookRead,
    WebhookUpdate,
)

__all__ = [  # noqa: RUF022
    # Database
    "AsyncSessionLocal",
    "Base",
    "get_async_session",
    "init_db",
    "auto_migrate",
    "engine",
    "DATABASE_URL",
    # Models
    "Target",
    "Record",
    "Task",
    "ApiKey",
    "Setting",
    "Relationship",
    "Error",
    "Webhook",
    "ModelBase",
    # Enums
    "TaskStatus",
    "RecordType",
    "RelationshipType",
    # Create schemas
    "TargetCreate",
    "RecordCreate",
    "TaskCreate",
    "ApiKeyCreate",
    "SettingCreate",
    "RelationshipCreate",
    "ErrorCreate",
    "WebhookCreate",
    # Update schemas
    "TargetUpdate",
    "RecordUpdate",
    "TaskUpdate",
    "ApiKeyUpdate",
    "SettingUpdate",
    "RelationshipUpdate",
    "ErrorUpdate",
    "WebhookUpdate",
    # Read schemas
    "TargetRead",
    "RecordRead",
    "TaskRead",
    "ApiKeyRead",
    "SettingRead",
    "RelationshipRead",
    "ErrorRead",
    "WebhookRead",
]
