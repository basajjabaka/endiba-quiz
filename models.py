"""
Database Models for Endiba Quiz Application
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Question(db.Model):
    """Question model storing quiz questions"""
    id = db.Column(db.Integer, primary_key=True)
    question_number = db.Column(db.Integer, unique=True, nullable=False)
    body = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.String(1), nullable=False)  # A, B, C, or D
    
    # Relationship to options
    options = db.relationship('Option', backref='question', lazy=True, cascade='all, delete-orphan')
    
    # Statistics (calculated on the fly)
    total_attempts = db.Column(db.Integer, default=0)
    correct_count = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<Question {self.question_number}: {self.body[:50]}...>'
    
    @property
    def correct_percentage(self):
        """Calculate percentage of correct answers"""
        if self.total_attempts == 0:
            return 0
        return (self.correct_count / self.total_attempts) * 100
    
    @property
    def wrong_percentage(self):
        """Calculate percentage of wrong answers"""
        if self.total_attempts == 0:
            return 0
        return 100 - self.correct_percentage


class Option(db.Model):
    """Option model storing answer choices for each question"""
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    label = db.Column(db.String(1), nullable=False)  # A, B, C, or D
    text = db.Column(db.Text, nullable=False)
    
    # Statistics
    selection_count = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<Option {self.label}: {self.text[:30]}...>'


class Attempt(db.Model):
    """Attempt model tracking quiz completions"""
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), nullable=False, index=True)
    score = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    time_taken = db.Column(db.Integer, nullable=False)  # Time in seconds
    
    # Relationship to responses
    responses = db.relationship('Response', backref='attempt', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Attempt by {self.ip_address}: {self.score}/10>'


class Response(db.Model):
    """Response model storing individual answer selections"""
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('attempt.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    selected_option = db.Column(db.String(1), nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<Response Q{self.question_id}: {self.selected_option} ({self.is_correct})>'
