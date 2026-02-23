"""
Endiba Quiz - Main Flask Application
"""
import os
import re
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, send_file
from werkzeug.utils import secure_filename
import plotly.utils
import pandas as pd

from config import Config
from models import db, Question, Option, Attempt, Response
from utils.parser import (
    parse_quiz_document, 
    save_questions_to_db, 
    get_questions_json,
    clear_all_questions,
    allowed_file
)

app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
db.init_app(app)


def get_client_ip():
    """Get client IP address"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr or '0.0.0.0'


def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


def check_ip_completed(ip_address):
    """Check if IP has already completed the quiz"""
    if not Config.IP_LOCK_ENABLED:
        return False
    
    attempt = Attempt.query.filter_by(ip_address=ip_address).first()
    return attempt is not None


# ==================== PUBLIC ROUTES ====================

@app.route('/')
def index():
    """Landing page"""
    ip = get_client_ip()
    has_completed = check_ip_completed(ip)
    
    # Get total questions
    question_count = Question.query.count()
    
    return render_template('index.html', 
                         has_completed=has_completed,
                         question_count=question_count)


@app.route('/quiz')
def quiz():
    """Quiz page - serves the quiz interface"""
    ip = get_client_ip()
    
    # Check if already completed
    if check_ip_completed(ip):
        return redirect(url_for('already_completed'))
    
    # Get questions
    questions = get_questions_json()
    
    if not questions:
        flash('No questions available. Please contact administrator.', 'error')
        return redirect(url_for('index'))
    
    # Store quiz start time
    session['quiz_start'] = datetime.utcnow().isoformat()
    session['ip_address'] = ip
    
    return render_template('quiz.html', questions=questions)


@app.route('/submit', methods=['POST'])
def submit_quiz():
    """Submit quiz answers"""
    ip = get_client_ip()
    
    # Check if already completed
    if check_ip_completed(ip):
        return redirect(url_for('already_completed'))
    
    # Calculate time taken
    quiz_start = session.get('quiz_start')
    if quiz_start:
        start_time = datetime.fromisoformat(quiz_start)
        time_taken = int((datetime.utcnow() - start_time).total_seconds())
    else:
        time_taken = 0
    
    # Get submitted answers
    data = request.get_json()
    answers = data.get('answers', {})
    
    # Calculate score and create attempt
    score = 0
    attempt = Attempt(
        ip_address=ip,
        score=0,  # Will update
        time_taken=time_taken
    )
    db.session.add(attempt)
    db.session.flush()
    
    responses_data = []
    
    for question_id, selected_option in answers.items():
        question = Question.query.get(int(question_id))
        if question:
            is_correct = selected_option.upper() == question.correct_answer.upper()
            if is_correct:
                score += 1
                question.correct_count += 1
            
            question.total_attempts += 1
            
            # Record option selection
            option = Option.query.filter_by(
                question_id=question.id,
                label=selected_option.upper()
            ).first()
            if option:
                option.selection_count += 1
            
            # Create response record
            response = Response(
                attempt_id=attempt.id,
                question_id=question.id,
                selected_option=selected_option.upper(),
                is_correct=is_correct
            )
            db.session.add(response)
            
            responses_data.append({
                'question_id': question.id,
                'question_number': question.question_number,
                'question_body': question.body,
                'selected_option': selected_option.upper(),
                'correct_option': question.correct_answer,
                'is_correct': is_correct,
                'options': [{
                    'label': opt.label,
                    'text': opt.text,
                    'is_selected': opt.label == selected_option.upper(),
                    'is_correct': opt.label == question.correct_answer
                } for opt in question.options]
            })
    
    # Update attempt score
    attempt.score = score
    db.session.commit()
    
    # Determine score color
    if score <= 3:
        score_color = 'red'
    elif score <= 6:
        score_color = 'orange'
    else:
        score_color = 'green'
    
    return jsonify({
        'success': True,
        'score': score,
        'total': 10,
        'score_color': score_color,
        'time_taken': time_taken,
        'responses': responses_data
    })


@app.route('/result')
def result():
    """Result page"""
    # This route is for template rendering, actual data comes from POST
    return render_template('result.html')


@app.route('/already-completed')
def already_completed():
    """Page shown when user has already completed the quiz"""
    attempt = Attempt.query.filter_by(ip_address=get_client_ip()).first()
    return render_template('already_completed.html', attempt=attempt)


# ==================== ADMIN ROUTES ====================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if (username == Config.ADMIN_USERNAME and 
            password == Config.ADMIN_PASSWORD):
            session['admin_logged_in'] = True
            session['admin_username'] = username
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('admin/login.html')


@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    return redirect(url_for('index'))


@app.route('/admin')
@admin_required
def admin_dashboard():
    """Admin dashboard with statistics"""
    # Get basic stats
    total_attempts = Attempt.query.count()
    completed_quiz = Attempt.query.count()
    total_clicks = completed_quiz + (session.get('quiz_started_count', 0))
    
    # Calculate completion rate
    started_quiz = total_clicks
    completion_rate = (completed_quiz / started_quiz * 100) if started_quiz > 0 else 0
    
    # Average time
    avg_time_result = db.session.query(
        db.func.avg(Attempt.time_taken)
    ).scalar()
    avg_time = int(avg_time_result) if avg_time_result else 0
    
    # Hourly activity data
    engine = db.session.bind
    dialect = engine.dialect.name if engine is not None else None

    if dialect == 'sqlite':
        hour_expression = db.func.strftime('%H', Attempt.timestamp)
    else:
        hour_expression = db.func.extract('hour', Attempt.timestamp)

    hourly_attempts = db.session.query(
        hour_expression.label('hour'),
        db.func.count(Attempt.id).label('count')
    ).group_by(hour_expression).all()
    
    hours = [0] * 24
    for hour, count in hourly_attempts:
        hour_int = int(hour)
        if 0 <= hour_int < 24:
            hours[hour_int] = count
    
    # Hourly activity chart
    hourly_chart = create_hourly_chart(hours)
    
    # Most answered correctly
    most_correct = Question.query.order_by(
        Question.correct_count.desc()
    ).limit(5).all()
    
    most_correct_data = [
        {
            'number': q.question_number,
            'body': q.body[:80] + '...' if len(q.body) > 80 else q.body,
            'correct_count': q.correct_count,
            'percentage': round(q.correct_percentage, 1)
        }
        for q in most_correct
    ]
    
    # Most answered wrongly (by wrong percentage)
    questions_with_wrong = [
        q for q in Question.query.all() 
        if q.total_attempts > 0 and q.wrong_percentage > 0
    ]
    most_wrong = sorted(
        questions_with_wrong, 
        key=lambda x: x.wrong_percentage, 
        reverse=True
    )[:5]
    
    most_wrong_data = [
        {
            'number': q.question_number,
            'body': q.body[:80] + '...' if len(q.body) > 80 else q.body,
            'wrong_count': q.total_attempts - q.correct_count,
            'percentage': round(q.wrong_percentage, 1)
        }
        for q in most_wrong
    ]
    
    # Per-question statistics
    question_stats = []
    for q in Question.query.order_by(Question.question_number).all():
        option_stats = []
        for opt in sorted(q.options, key=lambda x: x.label):
            option_stats.append({
                'label': opt.label,
                'text': opt.text,
                'count': opt.selection_count,
                'percentage': round((opt.selection_count / q.total_attempts * 100), 1) if q.total_attempts > 0 else 0
            })
        
        question_stats.append({
            'number': q.question_number,
            'body': q.body,
            'total_attempts': q.total_attempts,
            'correct_count': q.correct_count,
            'correct_percentage': round(q.correct_percentage, 1),
            'correct_answer': q.correct_answer,
            'options': option_stats
        })
    
    # Score distribution
    score_distribution = []
    for i in range(11):
        count = Attempt.query.filter_by(score=i).count()
        score_distribution.append({'score': i, 'count': count})
    
    score_chart = create_score_chart(score_distribution)
    
    return render_template(
        'admin/dashboard.html',
        total_attempts=total_attempts,
        completion_rate=round(completion_rate, 1),
        avg_time=avg_time,
        hourly_chart=hourly_chart,
        most_correct=most_correct_data,
        most_wrong=most_wrong_data,
        question_stats=question_stats,
        score_chart=score_chart
    )


def create_hourly_chart(hours):
    """Create hourly activity chart using Plotly"""
    import plotly.express as px
    import plotly.graph_objects as go
    
    df = pd.DataFrame({'Hour': range(24), 'Attempts': hours})
    
    fig = px.bar(
        df, 
        x='Hour', 
        y='Attempts',
        title='Quiz Activity by Hour of Day',
        labels={'Hour': 'Hour (0-23)', 'Attempts': 'Number of Attempts'},
        color='Attempts',
        color_continuous_scale='Blues'
    )
    
    fig.update_layout(
        xaxis=dict(tickmode='linear', tick0=0, dtick=1),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Inter, sans-serif")
    )
    
    return plotly.utils.PlotlyJSONEncoder().encode(fig)


def create_score_chart(distribution):
    """Create score distribution chart using Plotly"""
    import plotly.express as px
    
    df = pd.DataFrame(distribution)
    
    # Color based on score
    colors = []
    for s in df['score']:
        if s <= 3:
            colors.append('#EF4444')  # Red
        elif s <= 6:
            colors.append('#F59E0B')  # Orange
        else:
            colors.append('#10B981')  # Green
    
    fig = px.bar(
        df,
        x='score',
        y='count',
        title='Score Distribution',
        labels={'score': 'Score', 'count': 'Number of Users'},
        color_discrete_sequence=colors
    )
    
    fig.update_layout(
        xaxis=dict(tickmode='linear', tick0=0, dtick=1),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Inter, sans-serif")
    )
    
    return plotly.utils.PlotlyJSONEncoder().encode(fig)


@app.route('/admin/upload', methods=['GET', 'POST'])
@admin_required
def admin_upload():
    """Upload and parse Word document"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
            
            # Create upload folder if not exists
            os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
            
            file.save(filepath)
            
            # Parse document
            questions_data, parse_errors = parse_quiz_document(filepath)
            
            if not questions_data:
                flash(f'No questions found in document. Errors: {"; ".join(parse_errors)}', 'error')
                return redirect(request.url)
            
            # Save to database
            success_count, error_count, save_errors = save_questions_to_db(questions_data)
            
            # Clean up uploaded file
            try:
                os.remove(filepath)
            except:
                pass
            
            # Prepare message
            messages = []
            if success_count > 0:
                messages.append(f'Successfully imported {success_count} questions')
            if error_count > 0:
                messages.append(f'Failed to import {error_count} questions')
            if parse_errors:
                messages.append(f'Parse errors: {"; ".join(parse_errors[:5])}')
            if save_errors:
                messages.append(f'Save errors: {"; ".join(save_errors[:5])}')
            
            message = '; '.join(messages)
            if error_count == 0:
                flash(message, 'success')
            else:
                flash(message, 'warning')
            
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid file type. Please upload a .docx file', 'error')
    
    return render_template('admin/upload.html')


@app.route('/admin/clear', methods=['POST'])
@admin_required
def admin_clear():
    """Clear all quiz data"""
    success, errors = clear_all_questions()
    
    if success:
        flash('All quiz data cleared successfully', 'success')
    else:
        flash(f'Error clearing data: {"; ".join(errors)}', 'error')
    
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/export')
@admin_required
def admin_export():
    """Export quiz data as CSV"""
    attempts = Attempt.query.order_by(Attempt.timestamp.desc()).all()
    
    csv_data = 'IP Address,Score,Time Taken (s),Timestamp\n'
    for a in attempts:
        csv_data += f'{a.ip_address},{a.score},{a.time_taken},{a.timestamp}\n'
    
    return csv_data, 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename=quiz_results.csv'
    }


# ==================== API ROUTES ====================

@app.route('/api/questions')
def api_questions():
    """API endpoint to get questions"""
    questions = get_questions_json()
    return jsonify(questions)


@app.route('/api/stats')
def api_stats():
    """API endpoint for quick stats"""
    total_attempts = Attempt.query.count()
    avg_time_result = db.session.query(
        db.func.avg(Attempt.time_taken)
    ).scalar()
    avg_time = int(avg_time_result) if avg_time_result else 0
    
    return jsonify({
        'total_attempts': total_attempts,
        'average_time': avg_time
    })


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error='Page not found'), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error='Internal server error'), 500


# ==================== INITIALIZATION ====================

@app.cli.command('init-db')
def init_db_command():
    """Initialize the database"""
    with app.app_context():
        db.create_all()
        print('Database initialized successfully.')


if __name__ == '__main__':
    # Create upload folder
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    
    # Run app
    app.run(debug=True, host='0.0.0.0', port=5000)
