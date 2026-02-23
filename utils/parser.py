"""
Word Document Parser for Endiba Quiz
Parses questions from .docx files with specific format
"""
import re
from docx import Document
from models import Question, Option, db


def allowed_file(filename):
    """Check if file extension is allowed"""
    ALLOWED_EXTENSIONS = {'docx'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def parse_quiz_document(docx_path):
    """
    Parse a Word document and extract quiz questions
    
    Expected format:
    Question x: <question body>
    A. <option A>
    B. <option B>
    C. <option C>
    D. <option D>
    Question x Answer: <A/B/C/D>
    
    Returns:
        tuple: (questions_data, errors)
    """
    questions_data = []
    errors = []
    
    try:
        doc = Document(docx_path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        
        current_question = None
        current_options = {}
        current_answer = None
        
        for i, para in enumerate(paragraphs):
            # Match question pattern
            question_match = re.match(r'^Question\s+(\d+):\s*(.+)$', para, re.IGNORECASE)
            
            # Match option pattern
            option_match = re.match(r'^([A-D])\.\s*(.+)$', para, re.IGNORECASE)
            
            # Match answer pattern
            answer_match = re.match(r'^Question\s+\d+\s+Answer:\s*([A-D])$', para, re.IGNORECASE)
            
            if question_match:
                # If we have a previous question pending, save it
                if current_question is not None:
                    if current_answer is None:
                        errors.append(f"Question {current_question['number']} missing answer")
                        current_question['options'] = current_options
                        questions_data.append(current_question)
                    elif len(current_options) < 4:
                        errors.append(f"Question {current_question['number']} missing options")
                        current_question['options'] = current_options
                        questions_data.append(current_question)
                    else:
                        current_question['options'] = current_options
                        current_question['answer'] = current_answer
                        questions_data.append(current_question)
                
                # Start new question
                current_question = {
                    'number': int(question_match.group(1)),
                    'body': question_match.group(2).strip()
                }
                current_options = {}
                current_answer = None
                
            elif option_match and current_question is not None:
                label = option_match.group(1).upper()
                text = option_match.group(2).strip()
                current_options[label] = text
                
            elif answer_match and current_question is not None:
                current_answer = answer_match.group(1).upper()
                
            elif para and not para.startswith('#'):
                # Non-empty paragraph that doesn't match any pattern
                if current_question is not None:
                    errors.append(f"Unexpected line in Question {current_question['number']}: {para[:50]}...")
        
        # Don't forget the last question
        if current_question is not None:
            if current_answer is None:
                errors.append(f"Question {current_question['number']} missing answer")
                current_question['options'] = current_options
                questions_data.append(current_question)
            elif len(current_options) < 4:
                errors.append(f"Question {current_question['number']} missing options")
                current_question['options'] = current_options
                questions_data.append(current_question)
            else:
                current_question['options'] = current_options
                current_question['answer'] = current_answer
                questions_data.append(current_question)
        
        return questions_data, errors
        
    except Exception as e:
        errors.append(f"Error parsing document: {str(e)}")
        return [], errors


def save_questions_to_db(questions_data):
    """
    Save parsed questions to database
    
    Args:
        questions_data: List of question dictionaries
        
    Returns:
        tuple: (success_count, error_count, errors)
    """
    success_count = 0
    error_count = 0
    errors = []
    
    for q_data in questions_data:
        try:
            # Check if question already exists
            existing = Question.query.filter_by(question_number=q_data['number']).first()
            if existing:
                # Update existing question
                existing.body = q_data['body']
                existing.correct_answer = q_data['answer']
                
                # Update options
                for label, text in q_data['options'].items():
                    option = Option.query.filter_by(
                        question_id=existing.id, 
                        label=label
                    ).first()
                    if option:
                        option.text = text
                    else:
                        new_option = Option(
                            question_id=existing.id,
                            label=label,
                            text=text
                        )
                        db.session.add(new_option)
            else:
                # Create new question
                new_question = Question(
                    question_number=q_data['number'],
                    body=q_data['body'],
                    correct_answer=q_data['answer']
                )
                db.session.add(new_question)
                db.session.flush()  # Get the ID
                
                # Create options
                for label, text in q_data['options'].items():
                    new_option = Option(
                        question_id=new_question.id,
                        label=label,
                        text=text
                    )
                    db.session.add(new_option)
            
            success_count += 1
            
        except Exception as e:
            error_count += 1
            errors.append(f"Error saving Question {q_data['number']}: {str(e)}")
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        errors.append(f"Database commit error: {str(e)}")
        error_count = len(questions_data)
        success_count = 0
    
    return success_count, error_count, errors


def get_questions_json():
    """
    Get all questions in JSON format for frontend
    
    Returns:
        list: List of question dictionaries
    """
    questions = Question.query.order_by(Question.question_number).all()
    
    questions_data = []
    for q in questions:
        options = []
        for opt in sorted(q.options, key=lambda x: x.label):
            options.append({
                'label': opt.label,
                'text': opt.text
            })
        
        questions_data.append({
            'id': q.id,
            'number': q.question_number,
            'body': q.body,
            'correct_answer': q.correct_answer,
            'options': options
        })
    
    return questions_data


def clear_all_questions():
    """Clear all questions and options from database"""
    try:
        db.session.query(Response).delete()
        db.session.query(Attempt).delete()
        db.session.query(Option).delete()
        db.session.query(Question).delete()
        db.session.commit()
        return True, []
    except Exception as e:
        db.session.rollback()
        return False, [str(e)]
