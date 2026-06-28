from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel
from models import Conversation, Message, User
from database import get_db
import uuid

router = APIRouter(prefix="/conversations", tags=["conversations"])

@router.get("/{user_id}")
async def get_conversations(user_id: str, db: Session = Depends(get_db)):
    convs = db.query(Conversation).filter(
        or_(Conversation.user1_id == user_id, Conversation.user2_id == user_id)
    ).order_by(Conversation.updated_at.desc()).all()
    
    result = []
    for conv in convs:
        other_user = conv.user2 if conv.user1_id == user_id else conv.user1
        last_msg = db.query(Message).filter(Message.conversation_id == conv.id).order_by(Message.created_at.desc()).first()
        
        result.append({
            "id": conv.id,
            "other_user": {
                "id": other_user.id,
                "display_name": other_user.display_name,
                "avatar_url": other_user.avatar_url,
                "is_online": other_user.is_online
            },
            "last_message": last_msg.content if last_msg else None,
            "updated_at": conv.updated_at.isoformat()
        })
    
    return result

@router.post("/")
async def create_conversation(user1_id: str, user2_id: str, db: Session = Depends(get_db)):
    existing = db.query(Conversation).filter(
        or_(
            (Conversation.user1_id == user1_id) & (Conversation.user2_id == user2_id),
            (Conversation.user1_id == user2_id) & (Conversation.user2_id == user1_id)
        )
    ).first()
    
    if existing:
        return {"id": existing.id}
    
    conv = Conversation(
        id=str(uuid.uuid4()),
        user1_id=user1_id,
        user2_id=user2_id
    )
    db.add(conv)
    db.commit()
    return {"id": conv.id}