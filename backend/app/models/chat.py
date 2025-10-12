from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
import datetime

from app.models.applicant import Base


class ChatSession(Base):
    __tablename__ = 'chat_sessions'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    mode = Column(String, default='corpus')  # corpus | applicant | compare
    applicant_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    messages = relationship('ChatMessage', back_populates='session', cascade='all, delete-orphan')


class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('chat_sessions.id'))
    role = Column(String)  # user | assistant
    question = Column(Text, nullable=True)
    answer = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    session = relationship('ChatSession', back_populates='messages')
