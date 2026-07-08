from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_group_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    who_can_use_tags: Mapped[str] = mapped_column(String(16), default="all")
    allow_tag_list_view: Mapped[bool] = mapped_column(Boolean, default=True)
    restrict_tag_creation: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_delete_empty_tags: Mapped[bool] = mapped_column(Boolean, default=False)
    enable_change_log: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_quick_buttons: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    tags: Mapped[list["Tag"]] = relationship(back_populates="group", cascade="all, delete-orphan")
    users: Mapped[list["User"]] = relationship(back_populates="group", cascade="all, delete-orphan")
    change_logs: Mapped[list["ChangeLog"]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan",
    )
    editors: Mapped[list["GroupEditor"]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan",
    )


class GroupEditor(Base):
    __tablename__ = "group_editors"
    __table_args__ = (
        UniqueConstraint("group_id", "telegram_user_id", name="uq_editor_group_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    added_by_telegram_id: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    group: Mapped["Group"] = relationship(back_populates="editors")


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("group_id", "name", name="uq_tag_group_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))

    group: Mapped["Group"] = relationship(back_populates="tags")
    members: Mapped[list["User"]] = relationship(
        secondary="tag_users",
        back_populates="tags",
    )


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("group_id", "telegram_user_id", name="uq_user_group_telegram"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str] = mapped_column(String(128), default="")
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    group: Mapped["Group"] = relationship(back_populates="users")
    tags: Mapped[list["Tag"]] = relationship(
        secondary="tag_users",
        back_populates="members",
    )


class TagUser(Base):
    __tablename__ = "tag_users"

    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)


class ChangeLog(Base):
    __tablename__ = "change_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    actor_telegram_id: Mapped[int] = mapped_column(BigInteger)
    action: Mapped[str] = mapped_column(String(64))
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    group: Mapped["Group"] = relationship(back_populates="change_logs")
