from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from models import Message, Conversation
from database import get_db
import uuid
from datetime import datetime

router = APIRouter(prefix="/messages", tags=["messages"])

class MessageCreate(BaseModel):
    sender_id: str
    content: str
    conversation_id: str = None
    group_id: str = None

@router.get("/conversation/{conv_id}")
async def get_messages(conv_id: str, db: Session = Depends(get_db)):
    messages = db.query(Message).filter(Message.conversation_id == conv_id).order_by(Message.created_at).all()
    return [
        {
            "id": m.id,
            "sender_id": m.sender_id,
            "content": m.content,
            "created_at": m.created_at.isoformat(),
            "is_read": m.is_read,
            "is_delivered": m.is_delivered
        }
        for m in messages
    ]

@router.post("/")
async def create_message(msg: MessageCreate, db: Session = Depends(get_db)):
    new_msg = Message(
        id=str(uuid.uuid4()),
        sender_id=msg.sender_id,
        content=msg.content,
        conversation_id=msg.conversation_id,
        group_id=msg.group_id
    )
    db.add(new_msg)
    
    # Update conversation timestamp
    if msg.conversation_id:
        conv = db.query(Conversation).filter(Conversation.id == msg.conversation_id).first()
        if conv:
            conv.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(new_msg)
    return {
        "id": new_msg.id,
        "sender_id": new_msg.sender_id,
        "content": new_msg.content,
        "created_at": new_msg.created_at.isoformat()
    }

@router.patch("/{msg_id}/read")
async def mark_as_read(msg_id: str, db: Session = Depends(get_db)):
    msg = db.query(Message).filter(Message.id == msg_id).first()
    if msg:
        msg.is_read = True
        db.commit()
    return {"status": "ok"}