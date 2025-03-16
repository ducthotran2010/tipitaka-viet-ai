from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy import Column, Integer, String, JSON, DateTime, func, UniqueConstraint
from sqlalchemy.orm import Session
from .base import Base


class Reaction(Base):
    __tablename__ = 'reaction'
    __table_args__ = (UniqueConstraint('message_id', 'user_id',
                      'conversation_id', name='reaction__msg_user_conv_uc'),)

    id: int = Column(Integer, primary_key=True, index=True)
    message_id: str = Column(String, nullable=False)
    user_id: str = Column(String, nullable=False)
    conversation_id: str = Column(String, nullable=False)
    reaction: str = Column(String, nullable=False)
    request: Optional[Dict[str, Any]] = Column(JSON, nullable=False)
    created_at: datetime = Column(
        DateTime, server_default=func.now(), nullable=False)
    updated_at: datetime = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    @classmethod
    def upsert(
        cls,
        session: Session,
        message_id: str,
        user_id: str,
        conversation_id: str,
        reaction: str,
        request: Optional[Dict[str, Any]] = None
    ) -> "Reaction":
        instance = session.query(cls).filter_by(
            message_id=message_id,
            user_id=user_id,
            conversation_id=conversation_id
        ).first()
        if instance:
            instance.reaction = reaction
            instance.request = request
            session.commit()
            session.refresh(instance)
        else:
            instance = cls(
                message_id=message_id,
                user_id=user_id,
                conversation_id=conversation_id,
                reaction=reaction,
                request=request
            )
            session.add(instance)
            session.commit()
            session.refresh(instance)
        return instance


class Feedback(Base):
    __tablename__ = 'feedback'
    __table_args__ = (UniqueConstraint('message_id', 'user_id',
                      'conversation_id', name='feedback__msg_user_conv_uc'),)

    id: int = Column(Integer, primary_key=True, index=True)
    message_id: str = Column(String, nullable=False)
    user_id: str = Column(String, nullable=False)
    conversation_id: str = Column(String, nullable=False)
    feedback_type: str = Column(String, nullable=False)
    request: Optional[Dict[str, Any]] = Column(JSON, nullable=False)
    created_at: datetime = Column(
        DateTime, server_default=func.now(), nullable=False)
    updated_at: datetime = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    @classmethod
    def upsert(
        cls,
        session: Session,
        message_id: str,
        user_id: str,
        conversation_id: str,
        feedback_type: str,
        request: Optional[Dict[str, Any]] = None
    ) -> "Feedback":
        instance = session.query(cls).filter_by(
            message_id=message_id,
            user_id=user_id,
            conversation_id=conversation_id
        ).first()
        if instance:
            instance.feedback_type = feedback_type
            instance.request = request
            session.commit()
            session.refresh(instance)
        else:
            instance = cls(
                message_id=message_id,
                user_id=user_id,
                conversation_id=conversation_id,
                feedback_type=feedback_type,
                request=request
            )
            session.add(instance)
            session.commit()
            session.refresh(instance)
        return instance
