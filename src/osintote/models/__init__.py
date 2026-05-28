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
    AsyncSessionLocal,
    Base,
    get_async_session,
    init_db,
    auto_migrate,
    engine,
    DATABASE_URL,
)
from osintote.models.orm import (
    # Models
    Target,
    Record,
    Task,
    ApiKey,
    Setting,
    Relationship,
    Error,
    Webhook,
    ModelBase,
    # Enums
    TaskStatus,
    RecordType,
    RelationshipType,
    # Create schemas
    TargetCreate,
    RecordCreate,
    TaskCreate,
    ApiKeyCreate,
    SettingCreate,
    RelationshipCreate,
    ErrorCreate,
    WebhookCreate,
    # Update schemas
    TargetUpdate,
    RecordUpdate,
    TaskUpdate,
    ApiKeyUpdate,
    SettingUpdate,
    RelationshipUpdate,
    ErrorUpdate,
    WebhookUpdate,
    # Read schemas
    TargetRead,
    RecordRead,
    TaskRead,
    ApiKeyRead,
    SettingRead,
    RelationshipRead,
    ErrorRead,
    WebhookRead,
)

__all__ = [
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
