from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime, Text, Numeric, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class TestRun(Base):
    __tablename__ = "test_runs"

    test_run_id = Column(Integer, primary_key=True)
    description = Column(Text)
    date = Column(DateTime, default=datetime.utcnow)
    model_used = Column(String(50))
    parameters = Column(JSONB)
    cost = Column(Numeric)
    run_metadata = Column(JSONB)

    # Relationships
    inputs = relationship("PersonaInput", back_populates="test_run")
    personas = relationship("Persona", back_populates="test_run")
    stories = relationship("Story", back_populates="test_run")

class PersonaInput(Base):
    __tablename__ = "persona_inputs"

    input_id = Column(Integer, primary_key=True)
    persona_id = Column(Integer, ForeignKey('personas.persona_id', ondelete='CASCADE'))
    created_at = Column(DateTime, default=datetime.utcnow)
    prompt_id = Column(Integer, ForeignKey('prompts.prompt_id', ondelete='CASCADE'))
    extracted_themes = Column(JSONB)
    extracted_theme_count = Column(JSONB)
    detail_level = Column(String(20))
    response_text = Column(Text)
    response_stats = Column(JSONB)
    test_run_id = Column(Integer, ForeignKey('test_runs.test_run_id'))
    variation_id = Column(Integer)
    confidence = Column(JSONB, default=lambda: {"chunk": None, "theme": None, "score": 0.5})
    keyword_matches = Column(JSONB)
    passion_scores = Column(JSONB)
    user_prompt_prefs = Column(JSONB)

    # Relationships
    test_run = relationship("TestRun", back_populates="inputs")
    prompt = relationship("Prompt", back_populates="responses")
    persona = relationship("Persona", back_populates="inputs")

class Prompt(Base):
    __tablename__ = "prompts"

    prompt_id = Column(Integer, primary_key=True)
    prompt_text = Column(Text, nullable=False)
    prompt_theme = Column(JSONB)
    prompt_type = Column(String(50), nullable=False)
    prompt_complete = Column(JSONB)
    variations = Column(JSONB)

    # Relationships
    responses = relationship("PersonaInput", back_populates="prompt")

class Persona(Base):
    __tablename__ = "personas"

    persona_id = Column(Integer, primary_key=True)
    foundation = Column(JSONB, nullable=False)
    detail_level = Column(String(50), nullable=False)
    test_run_id = Column(Integer, ForeignKey('test_runs.test_run_id', ondelete='CASCADE'), nullable=False)
    system_message = Column(Text)
    clarity_scores = Column(JSONB)
    top_themes = Column(JSONB)
    passion_scores = Column(JSONB)

    # Relationships
    test_run = relationship("TestRun", back_populates="personas")
    inputs = relationship("PersonaInput", back_populates="persona")
    stories = relationship("Story", back_populates="persona")

    def get_theme_summary(self):
        """Get a summary of themes across all inputs"""
        themes = {}
        for input in self.inputs:
            if input.extracted_themes:
                for theme, score in input.extracted_themes.items():
                    themes[theme] = themes.get(theme, 0) + score
        return themes

class Story(Base):
    __tablename__ = "stories"

    story_id = Column(Integer, primary_key=True)
    persona_id = Column(Integer, ForeignKey('personas.persona_id', ondelete='CASCADE'))
    story_content = Column(Text)
    test_run_id = Column(Integer, ForeignKey('test_runs.test_run_id'))
    resonance_score = Column(Float)
    alignment_score = Column(Float)
    richness_score = Column(Float)
    emotional_tone_score = Column(Float)
    story_length = Column(Integer)
    novelty_score = Column(Float)
    variability_score = Column(Float)
    story_themes = Column(JSONB)
    story_metadata = Column(JSONB)
    story_prompts = Column(Text)

    # Relationships
    persona = relationship("Persona", back_populates="stories")
    test_run = relationship("TestRun", back_populates="stories")

class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    theme = Column(String(255), nullable=False)
    tags = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserInputHistory(Base):
    __tablename__ = "user_input_history"

    history_id = Column(Integer, primary_key=True)
    persona_id = Column(Integer, ForeignKey('personas.persona_id', ondelete='CASCADE'))
    test_run_id = Column(Integer, ForeignKey('test_runs.test_run_id', ondelete='CASCADE'))
    clarity_score = Column(JSONB)
    response_text = Column(JSONB)
    extracted_text = Column(JSONB)
    confidence_scores = Column(JSONB)
    story_content = Column(Text)
    version = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow) 