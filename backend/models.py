from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, Table, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

# Association table for group members
group_members = Table(
    'group_members',
    Base.metadata,
    Column('group_id', String, ForeignKey('groups.id')),
    Column('user_id', String, ForeignKey('users.id'))
)

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    phone_number = Column(String, unique=True, nullable=True)
    username = Column(String, unique=True)
    display_name = Column(String)
    avatar_url = Column(String, nullable=True)
    password_hash = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    is_online = Column(Boolean, default=False)
    
    conversations = relationship("Conversation", back_populates="user1")
    groups = relationship("Group", secondary=group_members, back_populates="members")
    messages = relationship("Message", back_populates="sender")

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user1_id = Column(String, ForeignKey('users.id'))
    user2_id = Column(String, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user1 = relationship("User", foreign_keys=[user1_id], back_populates="conversations")
    user2 = relationship("User", foreign_keys=[user2_id])
    messages = relationship("Message", back_populates="conversation")

class Group(Base):
    __tablename__ = "groups"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String)
    avatar_url = Column(String, nullable=True)
    created_by = Column(String, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    members = relationship("User", secondary=group_members, back_populates="groups")
    messages = relationship("Message", back_populates="group")

class Message(Base):
    __tablename__ = "messages"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_id = Column(String, ForeignKey('users.id'))
    conversation_id = Column(String, ForeignKey('conversations.id'), nullable=True)
    group_id = Column(String, ForeignKey('groups.id'), nullable=True)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)
    is_delivered = Column(Boolean, default=True)
    
    sender = relationship("User", back_populates="messages")
    conversation = relationship("Conversation", back_populates="messages")
    group = relationship("Group", back_populates="messages")