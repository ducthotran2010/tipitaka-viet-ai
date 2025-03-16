import secrets
from datetime import datetime
from typing import Dict, List, Callable, Any
from sqlalchemy.orm import Session
from db.postgres_models.authen import Authen  # Adjust this import according to your project structure


class APIKeyManager:
    def __init__(self, admin_key: str, session_factory: Callable[[], Session]) -> None:
        """
        Initialize the APIKeyManager with an admin key and a session factory.
        
        Args:
            admin_key (str): The administrative key used for privileged operations.
            session_factory (Callable[[], Session]): A callable that returns a new SQLAlchemy Session.
        """
        self.admin_key: str = admin_key
        self.session_factory: Callable[[], Session] = session_factory

    def generate_api_key(self, user: str, description: str = "") -> str:
        """
        Generate a new API key and store it in PostgreSQL.
        
        Args:
            user (str): The user associated with the API key.
            description (str, optional): A description for the API key.
            
        Returns:
            str: The generated API key.
        """
        api_key: str = secrets.token_urlsafe(32)
        session: Session = self.session_factory()
        try:
            # Use the Authen model's create classmethod to insert the record.
            Authen.create(
                session,
                key=api_key,
                user=user,
                description=description,
                is_active=True
            )
        finally:
            session.close()
        return api_key

    def validate_admin_key(self, admin_key: str) -> bool:
        """
        Check if the provided admin key is valid.
        
        Args:
            admin_key (str): The admin key to validate.
            
        Returns:
            bool: True if valid, False otherwise.
        """
        return admin_key == self.admin_key

    def validate_api_key(self, api_key: str) -> bool:
        """
        Check if the API key exists and is active in PostgreSQL.
        
        Args:
            api_key (str): The API key to validate.
            
        Returns:
            bool: True if the key exists and is active, False otherwise.
        """
        session: Session = self.session_factory()
        try:
            record: Authen = session.query(Authen).filter(Authen.key == api_key).first()
            return record is not None and record.is_active
        finally:
            session.close()

    def revoke_api_key(self, api_key: str) -> bool:
        """
        Revoke an API key in PostgreSQL by setting its `is_active` field to False.
        
        Args:
            api_key (str): The API key to revoke.
            
        Returns:
            bool: True if the key was found and revoked, False otherwise.
        """
        session: Session = self.session_factory()
        try:
            record: Authen = session.query(Authen).filter(Authen.key == api_key).first()
            if record:
                record.update(session, is_active=False)
                return True
            return False
        finally:
            session.close()

    def list_api_keys(self) -> List[Dict[str, Any]]:
        """
        List all API keys and their metadata from PostgreSQL.
        
        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each representing an API key record.
        """
        session: Session = self.session_factory()
        try:
            records: List[Authen] = session.query(Authen).all()
            return [record.to_dict() for record in records]
        finally:
            session.close()
