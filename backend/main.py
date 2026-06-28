from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import List
from datetime import datetime
import uuid

# DB Setup
DATABASE_URL = "sqlite:///./signal.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ===== MODELS =====
class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True)
    display_name = Column(String)
    password_hash = Column(String, default="mocked")
    is_online = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user1_id = Column(String, ForeignKey('users.id'))
    user2_id = Column(String, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Message(Base):
    __tablename__ = "messages"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_id = Column(String, ForeignKey('users.id'))
    conversation_id = Column(String, ForeignKey('conversations.id'), nullable=True)
    group_id = Column(String, ForeignKey('groups.id'), nullable=True)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)

class Group(Base):
    __tablename__ = "groups"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String)
    created_by = Column(String, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.utcnow)

class GroupMember(Base):
    __tablename__ = "group_members"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    group_id = Column(String, ForeignKey('groups.id'))
    user_id = Column(String, ForeignKey('users.id'))

Base.metadata.create_all(bind=engine)

# ===== SCHEMAS =====
class RegisterRequest(BaseModel):
    username: str
    display_name: str

class LoginRequest(BaseModel):
    username: str

class MessageCreate(BaseModel):
    sender_id: str
    conversation_id: str
    content: str

class GroupCreate(BaseModel):
    name: str
    created_by: str
    member_ids: List[str] = []

class GroupMessage(BaseModel):
    sender_id: str
    group_id: str
    content: str

# ===== FastAPI =====
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ===== ROUTES =====
@app.get("/health")
async def health():
    return {"status": "ok"}

# Auth
@app.post("/auth/register")
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        return {"error": "User exists"}
    user = User(username=req.username, display_name=req.display_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "username": user.username, "display_name": user.display_name}

@app.post("/auth/login")
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user:
        return {"error": "User not found"}
    return {"id": user.id, "username": user.username, "display_name": user.display_name}

@app.get("/users/{user_id}")
async def get_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"error": "Not found"}
    return {"id": user.id, "username": user.username, "display_name": user.display_name, "is_online": user.is_online}

# Conversations
@app.get("/conversations/{user_id}")
async def get_conversations(user_id: str, db: Session = Depends(get_db)):
    convs = db.query(Conversation).filter(
        (Conversation.user1_id == user_id) | (Conversation.user2_id == user_id)
    ).order_by(Conversation.updated_at.desc()).all()
    
    result = []
    for conv in convs:
        other_id = conv.user2_id if conv.user1_id == user_id else conv.user1_id
        other = db.query(User).filter(User.id == other_id).first()
        last_msg = db.query(Message).filter(Message.conversation_id == conv.id).order_by(Message.created_at.desc()).first()
        
        result.append({
            "id": conv.id,
            "other_user": {"id": other.id, "display_name": other.display_name, "is_online": other.is_online},
            "last_message": last_msg.content if last_msg else None,
            "updated_at": conv.updated_at.isoformat()
        })
    return result

@app.post("/conversations/")
async def create_conversation(user1_id: str, user2_id: str, db: Session = Depends(get_db)):
    existing = db.query(Conversation).filter(
        ((Conversation.user1_id == user1_id) & (Conversation.user2_id == user2_id)) |
        ((Conversation.user1_id == user2_id) & (Conversation.user2_id == user1_id))
    ).first()
    if existing:
        return {"id": existing.id}
    conv = Conversation(user1_id=user1_id, user2_id=user2_id)
    db.add(conv)
    db.commit()
    return {"id": conv.id}

# Messages (1-on-1)
@app.get("/messages/conversation/{conv_id}")
async def get_messages(conv_id: str, db: Session = Depends(get_db)):
    msgs = db.query(Message).filter(Message.conversation_id == conv_id).order_by(Message.created_at).all()
    return [
        {
            "id": m.id,
            "sender_id": m.sender_id,
            "content": m.content,
            "created_at": m.created_at.isoformat(),
            "is_read": m.is_read
        }
        for m in msgs
    ]

@app.post("/messages/")
async def create_message(msg: MessageCreate, db: Session = Depends(get_db)):
    new_msg = Message(sender_id=msg.sender_id, conversation_id=msg.conversation_id, content=msg.content)
    db.add(new_msg)
    conv = db.query(Conversation).filter(Conversation.id == msg.conversation_id).first()
    if conv:
        conv.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(new_msg)
    return {"id": new_msg.id, "sender_id": new_msg.sender_id, "content": new_msg.content, "created_at": new_msg.created_at.isoformat()}

# Groups
@app.post("/groups/")
async def create_group(req: GroupCreate, db: Session = Depends(get_db)):
    group = Group(name=req.name, created_by=req.created_by)
    db.add(group)
    db.commit()
    
    for member_id in req.member_ids + [req.created_by]:
        gm = GroupMember(group_id=group.id, user_id=member_id)
        db.add(gm)
    db.commit()
    
    return {"id": group.id, "name": group.name, "created_by": group.created_by}

@app.get("/groups/{user_id}")
async def get_user_groups(user_id: str, db: Session = Depends(get_db)):
    members = db.query(GroupMember).filter(GroupMember.user_id == user_id).all()
    result = []
    for m in members:
        group = db.query(Group).filter(Group.id == m.group_id).first()
        last_msg = db.query(Message).filter(Message.group_id == group.id).order_by(Message.created_at.desc()).first()
        result.append({
            "id": group.id,
            "name": group.name,
            "created_by": group.created_by,
            "last_message": last_msg.content if last_msg else None,
            "updated_at": group.created_at.isoformat()
        })
    return result

@app.get("/groups/{group_id}/members")
async def get_group_members(group_id: str, db: Session = Depends(get_db)):
    members = db.query(GroupMember).filter(GroupMember.group_id == group_id).all()
    result = []
    for m in members:
        user = db.query(User).filter(User.id == m.user_id).first()
        result.append({"id": user.id, "display_name": user.display_name})
    return result

@app.get("/messages/group/{group_id}")
async def get_group_messages(group_id: str, db: Session = Depends(get_db)):
    msgs = db.query(Message).filter(Message.group_id == group_id).order_by(Message.created_at).all()
    return [
        {
            "id": m.id,
            "sender_id": m.sender_id,
            "content": m.content,
            "created_at": m.created_at.isoformat(),
            "is_read": m.is_read
        }
        for m in msgs
    ]

@app.post("/messages/group")
async def create_group_message(msg: GroupMessage, db: Session = Depends(get_db)):
    new_msg = Message(sender_id=msg.sender_id, group_id=msg.group_id, content=msg.content)
    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)
    return {"id": new_msg.id, "sender_id": new_msg.sender_id, "content": new_msg.content, "created_at": new_msg.created_at.isoformat()}