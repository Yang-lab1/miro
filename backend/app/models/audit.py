from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import IdMixin, TimestampMixin


class AuditLog(Base, IdMixin, TimestampMixin):
    __tablename__ = "audit_logs"

    actor_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    action_key: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
