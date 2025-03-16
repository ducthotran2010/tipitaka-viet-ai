from typing import Optional, List, Any, Dict
from sqlalchemy import Column, Integer, String, DateTime, Boolean, func
from sqlalchemy.orm import Session
from .base import Base


class Authen(Base):
    __tablename__ = 'authen'

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, nullable=False)
    user = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(),
                        onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, default=True)

    def __repr__(self) -> str:
        return (
            f"<Authen(id={self.id}, key='{self.key}', user='{self.user}', "
            f"description='{self.description}', created_at='{self.created_at}', "
            f"updated_at='{self.updated_at}', is_active={self.is_active})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the Authen instance to a dictionary."""
        return {
            "id": self.id,
            "key": self.key,
            "user": self.user,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_active": self.is_active,
        }

    @classmethod
    def create(cls, session: Session, key: str, user: str,
               description: Optional[str] = None, is_active: bool = True) -> 'Authen':
        """Create a new Authen record and add it to the session."""
        auth = cls(key=key, user=user, description=description,
                   is_active=is_active)
        session.add(auth)
        session.commit()
        session.refresh(auth)
        return auth

    @classmethod
    def get_by_id(cls, session: Session, auth_id: int) -> Optional['Authen']:
        """Retrieve an Authen record by its id."""
        return session.query(cls).filter(cls.id == auth_id).first()

    @classmethod
    def get_all(cls, session: Session) -> List['Authen']:
        """Retrieve all Authen records."""
        return session.query(cls).all()

    def update(self, session: Session, **kwargs: Any) -> 'Authen':
        """Update attributes of the Authen record."""
        for attr, value in kwargs.items():
            if hasattr(self, attr):
                setattr(self, attr, value)
        session.commit()
        session.refresh(self)
        return self

    def delete(self, session: Session) -> None:
        """Delete the Authen record."""
        session.delete(self)
        session.commit()
