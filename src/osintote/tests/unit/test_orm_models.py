"""Unit tests for SQLModel ORM models.

Tests cover:
- Model creation and field validation
- Pydantic schema validation (Create/Update/Read)
- Enum correctness
- Relationship definitions
- Database table creation and queries (SQLite in-memory)
"""

from __future__ import annotations

import pytest
from uuid import uuid4
from datetime import datetime, timezone

from sqlmodel import SQLModel, Session, select
from sqlalchemy import create_engine

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
    # Schemas
    TargetCreate,
    TargetUpdate,
    TargetRead,
    RecordCreate,
    TaskCreate,
    ApiKeyCreate,
    SettingCreate,
    RelationshipCreate,
    ErrorCreate,
    WebhookCreate,
)


# ── fixture: in-memory SQLite database ──────────────────────────────


@pytest.fixture
def session():
    """Create an in-memory SQLite database with all tables."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


# ── tests: enums ─────────────────────────────────────────────────────


class TestEnums:
    """Verify enum values and membership."""

    def test_task_status_values(self) -> None:
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_record_type_values(self) -> None:
        assert RecordType.DNS.value == "dns"
        assert RecordType.HTTP.value == "http"
        assert RecordType.PORT.value == "port"
        assert RecordType.WHOIS.value == "whois"
        assert RecordType.SHODAN.value == "shodan"
        assert RecordType.CENSYS.value == "censys"
        assert RecordType.VIRUSTOTAL.value == "virustotal"
        assert RecordType.VULNERABILITY.value == "vulnerability"
        assert RecordType.GENERIC.value == "generic"

    def test_relationship_type_values(self) -> None:
        assert RelationshipType.HOST_OF.value == "host_of"
        assert RelationshipType.RESOLVES_TO.value == "resolves_to"
        assert RelationshipType.PTR.value == "ptr"
        assert RelationshipType.SUBDOMAIN.value == "subdomain"
        assert RelationshipType.PARENT_DOMAIN.value == "parent_domain"
        assert RelationshipType.IP_RANGE.value == "ip_range"
        assert RelationshipType.CUSTOM.value == "custom"


# ── tests: Target model ──────────────────────────────────────────────


class TestTargetModel:
    """Test Target model creation, validation, and CRUD."""

    def test_create_target(self, session: Session) -> None:
        target = Target(name="example.com", type="domain")
        session.add(target)
        session.commit()
        session.refresh(target)

        assert target.id is not None
        assert target.name == "example.com"
        assert target.type == "domain"
        assert target.raw is None
        assert target.tags == []
        assert target.created_at is not None
        assert target.updated_at is not None

    def test_create_target_with_tags(self, session: Session) -> None:
        target = Target(
            name="test.local",
            type="ip",
            raw="127.0.0.1",
            tags=["internal", "test"],
        )
        session.add(target)
        session.commit()
        session.refresh(target)

        assert target.tags == ["internal", "test"]

    def test_create_target_with_description(self, session: Session) -> None:
        target = Target(
            name="example.com",
            type="domain",
            description="A test domain",
        )
        session.add(target)
        session.commit()
        session.refresh(target)

        assert target.description == "A test domain"

    def test_query_targets_by_name(self, session: Session) -> None:
        target1 = Target(name="example.com", type="domain")
        target2 = Target(name="example.org", type="domain")
        session.add_all([target1, target2])
        session.commit()

        result = session.execute(select(Target).where(Target.name == "example.com"))
        assert result.first() is not None

    def test_query_targets_by_type(self, session: Session) -> None:
        target = Target(name="192.168.1.1", type="ip")
        session.add(target)
        session.commit()

        result = session.execute(select(Target).where(Target.type == "ip"))
        assert result.first() is not None


# ── tests: Pydantic schemas ─────────────────────────────────────────


class TestPydanticSchemas:
    """Test Pydantic Create/Update/Read schema validation."""

    def test_target_create_valid(self) -> None:
        schema = TargetCreate(
            name="example.com",
            type="domain",
            tags=["test"],
        )
        assert schema.name == "example.com"
        assert schema.type == "domain"
        assert schema.tags == ["test"]

    def test_target_create_min_length(self) -> None:
        with pytest.raises(Exception):  # Pydantic validation error
            TargetCreate(name="", type="domain")

    def test_target_update_optional(self) -> None:
        update = TargetUpdate(description="Updated")
        assert update.description == "Updated"
        assert update.name is None
        assert update.type is None

    def test_target_read_from_model(self) -> None:
        target = Target(
            name="example.com",
            type="domain",
            raw="example.com",
            tags=["prod"],
            description="Production domain",
        )
        read = TargetRead.model_validate(target)
        assert read.name == "example.com"
        assert read.type == "domain"
        assert read.id is None  # not yet persisted
        assert read.created_at is not None
        assert read.updated_at is not None


# ── tests: Record model ──────────────────────────────────────────────


class TestRecordModel:
    """Test Record model with JSON data storage."""

    def test_create_record(self, session: Session) -> None:
        target = Target(name="example.com", type="domain")
        session.add(target)
        session.commit()

        record = Record(
            target_id=target.id,
            type=RecordType.DNS,
            source="dnspython",
            data={"nameservers": ["ns1.example.com"], "a_records": ["93.184.216.34"]},
            confidence=0.95,
        )
        session.add(record)
        session.commit()
        session.refresh(record)

        assert record.source == "dnspython"
        assert record.confidence == 0.95
        assert record.data["nameservers"] == ["ns1.example.com"]

    def test_create_record_with_metadata(self, session: Session) -> None:
        record = Record(
            target_id=uuid4(),
            type=RecordType.HTTP,
            source="httpx",
            data={"status_code": 200, "headers": {"server": "nginx"}},
            metadata_={"custom_field": "value"},
        )
        session.add(record)
        session.commit()
        session.refresh(record)

        assert record.metadata_["custom_field"] == "value"

    def test_record_schema_validation(self) -> None:
        schema = RecordCreate(
            target_id=uuid4(),
            type=RecordType.DNS,
            source="test",
            data={"test": True},
            confidence=0.8,
        )
        assert schema.type == RecordType.DNS


# ── tests: Task model ────────────────────────────────────────────────


class TestTaskModel:
    """Test Task model with lifecycle states."""

    def test_create_task(self, session: Session) -> None:
        target = Target(name="example.com", type="domain")
        session.add(target)
        session.commit()

        task = Task(
            target_id=target.id,
            name="DNS enumeration",
            description="Run DNS lookup",
            recipe="full_domain_recon",
        )
        session.add(task)
        session.commit()
        session.refresh(task)

        assert task.status == TaskStatus.PENDING
        assert task.progress == 0.0
        assert task.recipe == "full_domain_recon"

    def test_task_status_transitions(self, session: Session) -> None:
        task = Task(name="Test task")
        session.add(task)
        session.commit()
        session.refresh(task)

        # Start task
        task.status = TaskStatus.RUNNING
        task.progress = 0.1
        task.started_at = datetime.now(timezone.utc)
        session.commit()

        # Complete task
        task.status = TaskStatus.COMPLETED
        task.progress = 1.0
        task.completed_at = datetime.now(timezone.utc)
        task.result = {"found": 5}
        session.commit()
        session.refresh(task)

        assert task.status == TaskStatus.COMPLETED
        assert task.progress == 1.0
        assert task.result == {"found": 5}

    def test_task_failed(self, session: Session) -> None:
        task = Task(
            name="Failing task",
            status=TaskStatus.FAILED,
            error_message="Connection timeout",
        )
        session.add(task)
        session.commit()
        session.refresh(task)

        assert task.status == TaskStatus.FAILED
        assert task.error_message == "Connection timeout"


# ── tests: ApiKey model ─────────────────────────────────────────────


class TestApiKeyModel:
    """Test ApiKey model with encrypted storage."""

    def test_create_api_key(self, session: Session) -> None:
        from pydantic import SecretStr

        key = ApiKey(
            name="shodan-prod",
            source="shodan",
            key=SecretStr("test-shodan-key"),
            primary=True,
        )
        session.add(key)
        session.commit()
        session.refresh(key)

        assert key.encrypted is True
        assert key.primary is True
        assert key.fallback is False


# ── tests: Setting model ────────────────────────────────────────────


class TestSettingModel:
    """Test Setting model for key-value storage."""

    def test_create_setting(self, session: Session) -> None:
        setting = Setting(
            key="ai.provider",
            value={"provider": "ollama", "model": "llama3"},
            description="AI provider configuration",
        )
        session.add(setting)
        session.commit()
        session.refresh(setting)

        assert setting.key == "ai.provider"
        assert setting.value["provider"] == "ollama"

    def test_setting_unique_key(self, session: Session) -> None:
        setting1 = Setting(key="test.key", value={"a": 1})
        session.add(setting1)
        session.commit()

        # Second setting with same key should fail on commit
        setting2 = Setting(key="test.key", value={"b": 2})
        session.add(setting2)

        with pytest.raises(Exception):  # IntegrityError
            session.commit()


# ── tests: Relationship model ───────────────────────────────────────


class TestRelationshipModel:
    """Test Relationship model for target linking."""

    def test_create_relationship(self, session: Session) -> None:
        target1 = Target(name="example.com", type="domain")
        target2 = Target(name="93.184.216.34", type="ip")
        session.add_all([target1, target2])
        session.commit()

        rel = Relationship(
            source_id=target1.id,
            target_id=target2.id,
            type=RelationshipType.RESOLVES_TO,
        )
        session.add(rel)
        session.commit()
        session.refresh(rel)

        assert rel.type == RelationshipType.RESOLVES_TO
        assert rel.source_id == target1.id
        assert rel.target_id == target2.id


# ── tests: Error model ──────────────────────────────────────────────


class TestErrorModel:
    """Test Error model for error tracking."""

    def test_create_error(self, session: Session) -> None:
        error = Error(
            severity="error",
            logger="osintote.engine",
            stage="dns_enumeration",
            message="DNS query timeout",
            meta={"query": "example.com", "timeout": 5},
        )
        session.add(error)
        session.commit()
        session.refresh(error)

        assert error.severity == "error"
        assert error.stage == "dns_enumeration"


# ── tests: Webhook model ────────────────────────────────────────────


class TestWebhookModel:
    """Test Webhook model for external notifications."""

    def test_create_webhook(self, session: Session) -> None:
        from pydantic import SecretStr

        webhook = Webhook(
            name="discord-alerts",
            url="https://discord.com/api/webhooks/123/abc",
            events=["on_task_complete", "on_critical_finding"],
            secret=SecretStr("webhook-secret"),
        )
        session.add(webhook)
        session.commit()
        session.refresh(webhook)

        assert webhook.enabled is True
        assert "on_task_complete" in webhook.events


# ── tests: relationships ─────────────────────────────────────────────


class TestRelationships:
    """Test SQLAlchemy relationship back-populates."""

    def test_target_has_records(self, session: Session) -> None:
        target = Target(name="example.com", type="domain")
        record = Record(
            target=target,
            type=RecordType.DNS,
            source="test",
            data={},
        )
        session.add(target)
        session.commit()

        session.refresh(target)
        assert len(target.records) == 1
        assert target.records[0].type == RecordType.DNS

    def test_task_belongs_to_target(self, session: Session) -> None:
        target = Target(name="example.com", type="domain")
        task = Task(
            target=target,
            name="Test task",
        )
        session.add(target)
        session.commit()

        session.refresh(target)
        assert len(target.tasks) == 1

    def test_relationship_links_targets(self, session: Session) -> None:
        target1 = Target(name="example.com", type="domain")
        target2 = Target(name="93.184.216.34", type="ip")
        session.add_all([target1, target2])
        session.commit()

        rel = Relationship(
            source=target1,
            target=target2,
            type=RelationshipType.RESOLVES_TO,
        )
        session.add(rel)
        session.commit()

        session.refresh(target1)
        session.refresh(target2)
        assert len(target1.in_relations) == 1
        assert len(target2.out_relations) == 1


# ── tests: ModelBase timestamps ─────────────────────────────────────


class TestModelBase:
    """Test inherited id and timestamp fields."""

    def test_model_has_uuid_id(self) -> None:
        model = ModelBase()
        assert hasattr(model, "id")
        assert hasattr(model, "created_at")
        assert hasattr(model, "updated_at")
