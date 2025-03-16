from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session
from .base import Base


class Conversation(Base):
    __tablename__ = 'conversation'

    id: int = Column(Integer, primary_key=True, index=True)
    conversation_id: str = Column(String, unique=True, nullable=False)
    system_prompt: Optional[str] = Column(String, nullable=True)
    last_bot_response: Optional[str] = Column(String, nullable=True)
    sender_id: Optional[str] = Column(String, nullable=True)  # New field added
    request: Optional[Dict[str, Any]] = Column(JSONB, nullable=True)
    created_at: datetime = Column(
        DateTime, server_default=func.now(), nullable=False)
    updated_at: datetime = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return (
            f"<Conversation(id={self.id}, conversation_id='{self.conversation_id}', "
            f"system_prompt='{self.system_prompt}', last_bot_response='{self.last_bot_response}', "
            f"sender_id='{self.sender_id}', request={self.request}, "
            f"created_at='{self.created_at}', updated_at='{self.updated_at}')>"
        )

    @classmethod
    def upsert(
        cls,
        session: Session,
        conversation_id: str,
        system_prompt: Optional[str] = None,
        last_bot_response: Optional[str] = None,
        request: Optional[Dict[str, Any]] = None,
        sender_id: Optional[str] = None
    ) -> "Conversation":
        instance = session.query(cls).filter_by(
            conversation_id=conversation_id).first()
        if instance:
            if system_prompt is not None:
                instance.system_prompt = system_prompt
            if last_bot_response is not None:
                instance.last_bot_response = last_bot_response
            if request is not None:
                instance.request = request
            if sender_id is not None:
                instance.sender_id = sender_id
            session.commit()
            session.refresh(instance)
        else:
            instance = cls(
                conversation_id=conversation_id,
                system_prompt=system_prompt,
                last_bot_response=last_bot_response,
                request=request,
                sender_id=sender_id
            )
            session.add(instance)
            session.commit()
            session.refresh(instance)
        return instance
