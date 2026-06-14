from sqlalchemy import (
    Column, String, Boolean, DateTime, Float, Integer, Text, ForeignKey, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class CharacterProfile(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "character_profiles"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    age_setting = Column(String(50), nullable=True)  # "17歳" など
    personality = Column(Text, nullable=True)
    tone = Column(Text, nullable=True)  # 口調
    first_person = Column(String(50), nullable=True)  # 一人称
    viewer_address = Column(String(50), nullable=True)  # 視聴者の呼び方
    specialty_genres = Column(JSON, nullable=True)  # 得意ジャンル
    weak_genres = Column(JSON, nullable=True)  # 苦手ジャンル
    character_description = Column(Text, nullable=True)
    ng_expressions = Column(Text, nullable=True)  # NG表現
    speech_samples = Column(Text, nullable=True)  # 話し方のサンプル

    # 音声設定
    tts_provider = Column(String(50), default="mock")  # openai|elevenlabs|voicevox|mock
    voice_type = Column(String(100), nullable=True)  # 声の種類/ID
    speech_rate = Column(Float, default=1.0)  # 話速
    pitch = Column(Float, default=0.0)  # ピッチ
    emotion_strength = Column(Float, default=0.7)  # 感情表現の強さ

    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)

    images = relationship("CharacterImage", back_populates="character", cascade="all, delete-orphan")


class CharacterImage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "character_images"

    character_id = Column(UUID(as_uuid=True), ForeignKey("character_profiles.id"), nullable=False)
    image_type = Column(String(50), nullable=False)
    # Types: profile | standing | expression_normal | expression_smile |
    #        expression_surprise | expression_troubled | expression_serious

    file_path = Column(String(500), nullable=True)
    file_url = Column(String(500), nullable=True)
    original_filename = Column(String(255), nullable=True)
    mime_type = Column(String(100), nullable=True)
    file_size = Column(Integer, nullable=True)

    character = relationship("CharacterProfile", back_populates="images")
