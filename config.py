"""
Configuration for Endiba Quiz Application
"""
import os

class Config:
    """Base configuration"""
    # Secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'endiba-quiz-secret-key-change-in-production'
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or 'sqlite:///endiba_quiz.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload folder for Word documents
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'docx'}
    
    # Quiz settings
    QUESTIONS_PER_QUIZ = 10
    IP_LOCK_ENABLED = True
    
    # Admin credentials (in production, use environment variables)
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME') or 'admin'
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'admin123'
