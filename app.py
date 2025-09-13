from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from forms import UserRegistrationForm, LoginForm, SubjectForm, ChapterForm, QuizForm, QuestionForm, UserProfileForm
from models import db, User, Subject, Chapter, Quiz, Question, QuizAttempt
from flask_login import login_required, login_user, logout_user, current_user, LoginManager
from datetime import datetime, date
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
import hashlib
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, SelectField
from wtforms.validators import DataRequired, NumberRange
import logging
from logging.handlers import RotatingFileHandler
import os
import argparse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO

# Create logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.mkdir('logs')

# Configure logging
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
file_handler = RotatingFileHandler('logs/quiz_master.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)

# Configure application logger
app = Flask(__name__)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Quiz Master startup')

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SHOW_ERROR_DETAILS'] = True  # Set to True to see detailed errors instead of 500.html
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create tables and admin user
with app.app_context():
    # Create all tables if they don't exist
    db.create_all()
    
    # Check if admin user exists
    admin = User.query.filter_by(username='admin@example.com').first()
    if not admin:
        # Create admin user
        admin = User(
            username='admin@example.com',
            password=hashlib.sha256('admin123'.encode()).hexdigest(),
            full_name='Administrator',
            qualification='Admin',
            dob=datetime.now().date(),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()

@app.route('/')
def index():
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.password == hashlib.sha256(form.password.data.encode()).hexdigest():
            login_user(user)
            flash('Login successful!', 'success')
            if user.username == 'admin@example.com':  
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('user_dashboard'))
    
    form = UserRegistrationForm()
    if form.validate_on_submit():
        try:
            # Check if user already exists
            if User.query.filter_by(username=form.username.data).first():
                flash('This email address is already registered. Please use a different email or login.', 'danger')
                return render_template('register.html', form=form, today_date=date.today().isoformat())
            
            new_user = User(
                username=form.username.data,
                password=hashlib.sha256(form.password.data.encode()).hexdigest(),
                full_name=form.full_name.data,
                qualification=form.qualification.data,
                dob=form.dob.data
            )
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'danger')
            app.logger.error(f'Registration error: {str(e)}')
    
    return render_template('register.html', form=form, today_date=date.today().isoformat())

@app.route('/logout')
@login_required
def logout_page():
    logout_user()
    return redirect(url_for('login'))

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    active_tab = request.args.get('tab', 'subject')
    subjects = Subject.query.all()
    users = User.query.all()
    
    return render_template('admin_dashboard.html', 
                         subjects=subjects, 
                         users=users, 
                         active_tab=active_tab)

@app.route('/quiz_management')
@login_required
def quiz_management():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Get all subjects with their chapters and quizzes
        subjects = Subject.query.all()
        
        # The relationships are already loaded due to lazy=True in the models
        # No need to force load them with .all()
        
        return render_template('quiz_management.html', subjects=subjects)
    except Exception as e:
        app.logger.error(f'Quiz Management Error: {str(e)}')
        flash('An error occurred while loading quiz management.', 'danger')
        return redirect(url_for('admin_dashboard'))

@app.route('/manage_questions/<int:quiz_id>')
@login_required
def manage_questions(quiz_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    quiz = Quiz.query.get_or_404(quiz_id)
    return render_template('manage_questions.html', quiz=quiz)

@app.route('/add_quiz/<int:chapter_id>', methods=['GET', 'POST'])
@login_required
def add_quiz(chapter_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    chapter = Chapter.query.get_or_404(chapter_id)
    form = QuizForm()
    
    if form.validate_on_submit():
        quiz = Quiz(
            time_duration=form.time_duration.data,
            remarks=form.remarks.data,
            chapter_id=chapter_id
        )
        db.session.add(quiz)
        try:
            db.session.commit()
            flash('Quiz added successfully.', 'success')
            return redirect(url_for('quiz_management'))
        except:
            db.session.rollback()
            flash('An error occurred while adding the quiz.', 'danger')
    
    return render_template('add_quiz.html', form=form, chapter=chapter)

@app.route('/edit_quiz/<int:quiz_id>', methods=['GET', 'POST'])
@login_required
def edit_quiz(quiz_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    quiz = Quiz.query.get_or_404(quiz_id)
    form = QuizForm(obj=quiz)
    
    if form.validate_on_submit():
        quiz.time_duration = form.time_duration.data
        quiz.remarks = form.remarks.data
        try:
            db.session.commit()
            flash('Quiz updated successfully.', 'success')
            return redirect(url_for('quiz_management'))
        except:
            db.session.rollback()
            flash('An error occurred while updating the quiz.', 'danger')
    
    return render_template('edit_quiz.html', form=form, quiz=quiz)

@app.route('/delete_quiz/<int:quiz_id>', methods=['POST'])
@login_required
def delete_quiz(quiz_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    quiz = Quiz.query.get_or_404(quiz_id)
    try:
        # Delete all questions and attempts associated with this quiz
        Question.query.filter_by(quiz_id=quiz_id).delete()
        QuizAttempt.query.filter_by(quiz_id=quiz_id).delete()
        db.session.delete(quiz)
        db.session.commit()
        flash('Quiz deleted successfully.', 'success')
    except:
        db.session.rollback()
        flash('An error occurred while deleting the quiz.', 'danger')
    
    return redirect(url_for('quiz_management'))

@app.route('/add_question/<int:quiz_id>', methods=['GET', 'POST'])
@login_required
def add_question(quiz_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    try:
        quiz = Quiz.query.get_or_404(quiz_id)
        form = QuestionForm()
        
        if form.validate_on_submit():
            try:
                # Get the actual option value based on the selected option
                selected_option = form.correct_option.data
                correct_answer = getattr(form, selected_option).data
                
                question = Question(
                    question_statement=form.question_statement.data,
                    option1=form.option1.data,
                    option2=form.option2.data,
                    option3=form.option3.data,
                    option4=form.option4.data,
                    correct_option=correct_answer,  # Store the actual answer text
                    quiz_id=quiz_id
                )
                db.session.add(question)
                db.session.commit()
                flash('Question added successfully.', 'success')
                return redirect(url_for('manage_questions', quiz_id=quiz_id))
            except Exception as e:
                db.session.rollback()
                app.logger.error(f'Error adding question: {str(e)}')
                flash('An error occurred while adding the question.', 'danger')
        
        return render_template('add_question.html', form=form, quiz=quiz)
    except Exception as e:
        app.logger.error(f'Error in add_question route: {str(e)}')
        flash('An error occurred. Please try again.', 'danger')
        return redirect(url_for('quiz_management'))

@app.route('/edit_question/<int:question_id>', methods=['GET', 'POST'])
@login_required
def edit_question(question_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    question = Question.query.get_or_404(question_id)
    form = QuestionForm(obj=question)
    
    if form.validate_on_submit():
        question.question_statement = form.question_statement.data
        question.option1 = form.option1.data
        question.option2 = form.option2.data
        question.option3 = form.option3.data
        question.option4 = form.option4.data
        question.correct_option = form.correct_option.data
        try:
            db.session.commit()
            flash('Question updated successfully.', 'success')
            return redirect(url_for('manage_questions', quiz_id=question.quiz_id))
        except:
            db.session.rollback()
            flash('An error occurred while updating the question.', 'danger')
    
    return render_template('edit_question.html', form=form, question=question)

@app.route('/delete_question/<int:question_id>', methods=['POST'])
@login_required
def delete_question(question_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    question = Question.query.get_or_404(question_id)
    quiz_id = question.quiz_id
    try:
        db.session.delete(question)
        db.session.commit()
        flash('Question deleted successfully.', 'success')
    except:
        db.session.rollback()
        flash('An error occurred while deleting the question.', 'danger')
    
    return redirect(url_for('manage_questions', quiz_id=quiz_id))

@app.route('/user_dashboard')
@login_required
def user_dashboard():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))

    # Get quizzes with at least one question
    quizzes = Quiz.query\
        .join(Chapter, Quiz.chapter_id == Chapter.id)\
        .join(Subject, Chapter.subject_id == Subject.id)\
        .join(Question, Quiz.id == Question.quiz_id)\
        .group_by(Quiz.id)\
        .having(db.func.count(Question.id) > 0)\
        .all()

    # Get all attempts for trend chart
    all_attempts = QuizAttempt.query\
        .filter_by(user_id=current_user.id)\
        .order_by(QuizAttempt.attempt_date.asc())\
        .all()

    # Get only 2 recent attempts for display
    recent_attempts = QuizAttempt.query\
        .filter_by(user_id=current_user.id)\
        .order_by(QuizAttempt.attempt_date.desc())\
        .limit(2)\
        .all()

    # Convert recent attempts to serializable format
    recent_attempts_data = []
    for attempt in recent_attempts:
        quiz = Quiz.query.get(attempt.quiz_id)
        recent_attempts_data.append({
            'quiz_name': quiz.remarks if quiz else 'Unknown Quiz',
            'score': attempt.score,
            'total_questions': attempt.total_questions,
            'attempt_date': attempt.attempt_date.strftime('%Y-%m-%d %H:%M:%S')
        })

    # Convert all attempts to serializable format for trend chart
    trend_data = []
    for attempt in all_attempts:
        quiz = Quiz.query.get(attempt.quiz_id)
        trend_data.append({
            'quiz_name': quiz.remarks if quiz else 'Unknown Quiz',
            'score': attempt.score,
            'total_questions': attempt.total_questions,
            'attempt_date': attempt.attempt_date.strftime('%Y-%m-%d'),
            'percentage': round((attempt.score / attempt.total_questions * 100), 1)
        })

    # Calculate subject-wise performance using a single query
    subject_stats = db.session.query(
        Subject.name,
        db.func.count(QuizAttempt.id).label('total_attempts'),
        db.func.avg(db.func.cast(QuizAttempt.score * 100.0 / QuizAttempt.total_questions, db.Float)).label('avg_score')
    ).join(Chapter, Subject.id == Chapter.subject_id)\
     .join(Quiz, Chapter.id == Quiz.chapter_id)\
     .join(QuizAttempt, Quiz.id == QuizAttempt.quiz_id)\
     .filter(QuizAttempt.user_id == current_user.id)\
     .group_by(Subject.id, Subject.name)\
     .all()

    stats = []
    for subject in subject_stats:
        stats.append({
            'subject': subject.name,
            'attempts': subject.total_attempts,
            'avg_score': round(subject.avg_score, 1) if subject.avg_score is not None else 0
        })

    return render_template('user_dashboard.html', 
                         quizzes=quizzes, 
                         recent_attempts=recent_attempts_data,
                         subject_stats=stats,
                         trend_data=trend_data)

@app.route('/attempt_quiz/<int:quiz_id>', methods=['GET', 'POST'])
@login_required
def attempt_quiz(quiz_id):
    if current_user.is_admin:
        flash('Admins cannot attempt quizzes.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    quiz = Quiz.query.get_or_404(quiz_id)
    if request.method == 'POST':
        try:
            score = 0
            total_questions = len(quiz.questions)
            
            for question in quiz.questions:
                selected_option = request.form.get(f'question_{question.id}')
                if selected_option:  # Check if an option was selected
                    # Get the actual answer text based on the selected option
                    selected_answer = getattr(question, selected_option, None)
                    if selected_answer == question.correct_option:
                        score += 1
            
            quiz_attempt = QuizAttempt(
                user_id=current_user.id,
                quiz_id=quiz_id,
                score=score,
                total_questions=total_questions,
                attempt_date=datetime.now()
            )
            db.session.add(quiz_attempt)
            db.session.commit()
            
            percentage = (score / total_questions * 100) if total_questions > 0 else 0
            flash(f'Quiz submitted successfully! Your score: {score}/{total_questions} ({percentage:.1f}%)', 'success')
            return redirect(url_for('user_dashboard'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Error submitting quiz: {str(e)}')
            flash('An error occurred while submitting your quiz. Please try again.', 'danger')
            return redirect(url_for('user_dashboard'))
    
    return render_template('attempt_quiz.html', quiz=quiz)

@app.route('/user/scores')
@login_required
def user_scores():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    
    attempts = QuizAttempt.query.filter_by(user_id=current_user.id).all()
    return render_template('user_scores.html', attempts=attempts)

@app.route('/user/summary')
@login_required
def user_summary():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    
    # Get all attempts by the user
    attempts = QuizAttempt.query.filter_by(user_id=current_user.id).all()
    
    # Get unique attempted quiz IDs
    attempted_quiz_ids = set(attempt.quiz_id for attempt in attempts)
    total_unique_quizzes = len(attempted_quiz_ids)
    
    # Calculate overall statistics
    if attempts:
        total_score = sum(attempt.score for attempt in attempts)
        total_questions = sum(attempt.total_questions for attempt in attempts)
        average_score = (total_score / total_questions) * 100 if total_questions > 0 else 0
        best_score = max((attempt.score / attempt.total_questions * 100) for attempt in attempts) if attempts else 0
    else:
        average_score = 0
        best_score = 0
    
    # Get all available quizzes with their attempt status
    available_quizzes = []
    quizzes = Quiz.query.join(Chapter).join(Subject).all()
    for quiz in quizzes:
        available_quizzes.append({
            'name': quiz.remarks,
            'chapter': quiz.chapter.name,
            'subject': quiz.chapter.subject.name,
            'is_attempted': quiz.id in attempted_quiz_ids
        })
    
    total_available_quizzes = len(quizzes)
    
    # Get subject-wise statistics
    subject_stats = {}
    subject_labels = []
    subject_scores = []
    
    for attempt in attempts:
        quiz = Quiz.query.join(Chapter).join(Subject).filter(Quiz.id == attempt.quiz_id).first()
        if quiz:
            subject_name = quiz.chapter.subject.name
            if subject_name not in subject_stats:
                subject_stats[subject_name] = {
                    'attempts': 0,
                    'total_score': 0,
                    'total_questions': 0
                }
            stats = subject_stats[subject_name]
            stats['attempts'] += 1
            stats['total_score'] += attempt.score
            stats['total_questions'] += attempt.total_questions
    
    # Calculate percentages and prepare chart data
    for subject_name, stats in subject_stats.items():
        percentage = (stats['total_score'] / stats['total_questions']) * 100 if stats['total_questions'] > 0 else 0
        subject_labels.append(subject_name)
        subject_scores.append(round(percentage, 2))
    
    # Get month-wise attempt statistics
    month_stats = {}
    for attempt in attempts:
        month_key = attempt.attempt_date.strftime('%Y-%m')
        if month_key not in month_stats:
            month_stats[month_key] = {
                'month_name': attempt.attempt_date.strftime('%B %Y'),
                'attempts': 0,
                'total_score': 0,
                'total_questions': 0,
                'quizzes': set()
            }
        stats = month_stats[month_key]
        stats['attempts'] += 1
        stats['total_score'] += attempt.score
        stats['total_questions'] += attempt.total_questions
        stats['quizzes'].add(attempt.quiz_id)
    
    # Convert month stats to list and calculate percentages
    month_wise_stats = []
    for month_key in sorted(month_stats.keys(), reverse=True):
        stats = month_stats[month_key]
        percentage = (stats['total_score'] / stats['total_questions'] * 100) if stats['total_questions'] > 0 else 0
        month_wise_stats.append({
            'month': stats['month_name'],
            'attempts': stats['attempts'],
            'unique_quizzes': len(stats['quizzes']),
            'score': round(percentage, 1)
        })
    
    return render_template('user_summary.html',
                         total_quizzes=total_unique_quizzes,
                         average_score=average_score,
                         best_score=best_score,
                         total_available_quizzes=total_available_quizzes,
                         subject_labels=subject_labels,
                         subject_scores=subject_scores,
                         available_quizzes=available_quizzes,
                         month_wise_stats=month_wise_stats)

@app.route('/user/summary/download')
@login_required
def download_summary():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    
    # Create a BytesIO buffer to receive PDF data
    buffer = BytesIO()
    
    # Create the PDF object using ReportLab
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Add title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30
    )
    elements.append(Paragraph("Quiz Performance Summary", title_style))
    elements.append(Spacer(1, 20))
    
    # Get user's quiz attempts
    attempts = QuizAttempt.query.filter_by(user_id=current_user.id).all()
    
    # Calculate overall statistics
    total_unique_quizzes = len(set(attempt.quiz_id for attempt in attempts))
    if attempts:
        total_score = sum(attempt.score for attempt in attempts)
        total_questions = sum(attempt.total_questions for attempt in attempts)
        average_score = (total_score / total_questions * 100) if total_questions > 0 else 0
    else:
        average_score = 0
    
    # Add overall statistics
    elements.append(Paragraph("Overall Statistics", styles['Heading2']))
    overall_data = [
        ["Total Quizzes Attempted", str(total_unique_quizzes)],
        ["Average Score", f"{average_score:.1f}%"]
    ]
    overall_table = Table(overall_data)
    overall_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(overall_table)
    elements.append(Spacer(1, 20))
    
    # Add month-wise statistics
    elements.append(Paragraph("Month-wise Statistics", styles['Heading2']))
    
    month_stats = {}
    for attempt in attempts:
        month_key = attempt.attempt_date.strftime('%Y-%m')
        if month_key not in month_stats:
            month_stats[month_key] = {
                'month_name': attempt.attempt_date.strftime('%B %Y'),
                'attempts': 0,
                'total_score': 0,
                'total_questions': 0,
                'quizzes': set()
            }
        stats = month_stats[month_key]
        stats['attempts'] += 1
        stats['total_score'] += attempt.score
        stats['total_questions'] += attempt.total_questions
        stats['quizzes'].add(attempt.quiz_id)
    
    # Create month-wise table data
    month_data = [["Month", "Total Attempts", "Unique Quizzes", "Average Score"]]
    for month_key in sorted(month_stats.keys(), reverse=True):
        stats = month_stats[month_key]
        percentage = (stats['total_score'] / stats['total_questions'] * 100) if stats['total_questions'] > 0 else 0
        month_data.append([
            stats['month_name'],
            str(stats['attempts']),
            str(len(stats['quizzes'])),
            f"{percentage:.1f}%"
        ])
    
    month_table = Table(month_data)
    month_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER')
    ]))
    elements.append(month_table)
    
    # Build the PDF document
    doc.build(elements)
    
    # Move to the beginning of the buffer
    buffer.seek(0)
    
    # Return the PDF file
    return send_file(
        buffer,
        download_name=f'quiz_summary_{datetime.now().strftime("%Y%m%d")}.pdf',
        as_attachment=True,
        mimetype='application/pdf'
    )

@app.route('/admin_summary')
@login_required
def admin_summary():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('user_dashboard'))
    
    # Get all subjects and users
    subjects = Subject.query.all()
    users = User.query.filter_by(is_admin=False).all()
    
    # Calculate summary statistics
    total_subjects = len(subjects)
    total_chapters = sum(len(subject.chapters) for subject in subjects)
    total_quizzes = sum(len(chapter.quizzes) for subject in subjects for chapter in subject.chapters)
    total_questions = sum(len(quiz.questions) for subject in subjects for chapter in subject.chapters for quiz in chapter.quizzes)
    total_users = len(users)
    
    # Get top scores for each quiz
    top_scores = []
    quizzes = Quiz.query.all()
    for quiz in quizzes:
        # Get all attempts for this quiz
        attempts = QuizAttempt.query.filter_by(quiz_id=quiz.id).all()
        # Count unique users who attempted this quiz
        unique_users = len(set(attempt.user_id for attempt in attempts))
        
        # Get the highest score for this quiz
        best_attempt = QuizAttempt.query.filter_by(quiz_id=quiz.id)\
            .order_by((QuizAttempt.score * 100.0 / QuizAttempt.total_questions).desc())\
            .first()
        
        if best_attempt:
            # Get the user who achieved this score
            user = User.query.get(best_attempt.user_id)
            percentage = (best_attempt.score / best_attempt.total_questions * 100)
            
            top_scores.append({
                'quiz_name': quiz.remarks,
                'chapter': quiz.chapter.name,
                'subject': quiz.chapter.subject.name,
                'user': user.full_name,
                'score': best_attempt.score,
                'total': best_attempt.total_questions,
                'percentage': round(percentage, 1),
                'date': best_attempt.attempt_date.strftime('%Y-%m-%d'),
                'attempts': unique_users
            })
    
    # Sort top scores by percentage in descending order
    top_scores.sort(key=lambda x: x['percentage'], reverse=True)
    
    # Get subject-wise quiz attempts
    subject_attempts = []
    for subject in subjects:
        # Count attempts for all quizzes in this subject
        attempt_count = db.session.query(db.func.count(QuizAttempt.id))\
            .join(Quiz, QuizAttempt.quiz_id == Quiz.id)\
            .join(Chapter, Quiz.chapter_id == Chapter.id)\
            .filter(Chapter.subject_id == subject.id)\
            .scalar()
        
        if attempt_count > 0:
            subject_attempts.append({
                'subject_name': subject.name,
                'total_attempts': attempt_count
            })
    
    # Sort subject attempts by number of attempts in descending order
    subject_attempts.sort(key=lambda x: x['total_attempts'], reverse=True)
    
    summary = {
        'total_subjects': total_subjects,
        'total_chapters': total_chapters,
        'total_quizzes': total_quizzes,
        'total_questions': total_questions,
        'total_users': total_users
    }
    
    return render_template('admin_summary.html', 
                         subjects=subjects,
                         users=users,
                         summary=summary,
                         top_scores=top_scores,
                         subject_attempts=subject_attempts)

@app.route('/add_subject', methods=['GET', 'POST'])
@login_required
def add_subject():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    form = SubjectForm()
    if form.validate_on_submit():
        subject = Subject(
            name=form.name.data,
            description=form.description.data
        )
        db.session.add(subject)
        try:
            db.session.commit()
            flash('Subject added successfully.', 'success')
            return redirect(url_for('admin_dashboard'))
        except:
            db.session.rollback()
            flash('An error occurred while adding the subject.', 'danger')
    
    return render_template('add_subject.html', form=form)

@app.route('/edit_subject/<int:subject_id>', methods=['GET', 'POST'])
@login_required
def edit_subject(subject_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    subject = Subject.query.get_or_404(subject_id)
    form = SubjectForm(obj=subject)
    
    if form.validate_on_submit():
        subject.name = form.name.data
        subject.description = form.description.data
        try:
            db.session.commit()
            flash('Subject updated successfully.', 'success')
            return redirect(url_for('admin_dashboard'))
        except:
            db.session.rollback()
            flash('An error occurred while updating the subject.', 'danger')
    
    return render_template('edit_subject.html', form=form, subject=subject)

@app.route('/delete_subject/<int:subject_id>', methods=['POST'])
@login_required
def delete_subject(subject_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    subject = Subject.query.get_or_404(subject_id)
    try:
        # Delete all chapters and their associated quizzes and attempts
        for chapter in subject.chapters:
            for quiz in chapter.quizzes:
                Question.query.filter_by(quiz_id=quiz.id).delete()
                QuizAttempt.query.filter_by(quiz_id=quiz.id).delete()
                db.session.delete(quiz)
            db.session.delete(chapter)
        db.session.delete(subject)
        db.session.commit()
        flash('Subject deleted successfully.', 'success')
    except:
        db.session.rollback()
        flash('An error occurred while deleting the subject.', 'danger')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/add_chapter/<int:subject_id>', methods=['GET', 'POST'])
@login_required
def add_chapter(subject_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    subject = Subject.query.get_or_404(subject_id)
    form = ChapterForm()
    
    if form.validate_on_submit():
        chapter = Chapter(
            name=form.name.data,
            description=form.description.data,
            subject_id=subject_id
        )
        db.session.add(chapter)
        try:
            db.session.commit()
            flash('Chapter added successfully.', 'success')
            return redirect(url_for('admin_dashboard'))
        except:
            db.session.rollback()
            flash('An error occurred while adding the chapter.', 'danger')
    
    return render_template('add_chapter.html', form=form, subject=subject)

@app.route('/edit_chapter/<int:chapter_id>', methods=['GET', 'POST'])
@login_required
def edit_chapter(chapter_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    chapter = Chapter.query.get_or_404(chapter_id)
    form = ChapterForm(obj=chapter)
    
    if form.validate_on_submit():
        chapter.name = form.name.data
        chapter.description = form.description.data
        try:
            db.session.commit()
            flash('Chapter updated successfully.', 'success')
            return redirect(url_for('admin_dashboard'))
        except:
            db.session.rollback()
            flash('An error occurred while updating the chapter.', 'danger')
    
    return render_template('edit_chapter.html', form=form, chapter=chapter)

@app.route('/delete_chapter/<int:chapter_id>', methods=['POST'])
@login_required
def delete_chapter(chapter_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    chapter = Chapter.query.get_or_404(chapter_id)
    try:
        # Delete all quizzes and their associated questions and attempts
        for quiz in chapter.quizzes:
            Question.query.filter_by(quiz_id=quiz.id).delete()
            QuizAttempt.query.filter_by(quiz_id=quiz.id).delete()
            db.session.delete(quiz)
        db.session.delete(chapter)
        db.session.commit()
        flash('Chapter deleted successfully.', 'success')
    except:
        db.session.rollback()
        flash('An error occurred while deleting the chapter.', 'danger')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if current_user.is_admin:
        flash('Admin profile cannot be modified.', 'warning')
        return redirect(url_for('admin_dashboard'))
    
    form = UserProfileForm(obj=current_user)
    
    if form.validate_on_submit():
        try:
            # Update basic information
            current_user.full_name = form.full_name.data
            current_user.qualification = form.qualification.data
            current_user.dob = form.dob.data
            
            # Handle password change if requested
            if form.new_password.data:
                # Verify current password
                if current_user.password != hashlib.sha256(form.current_password.data.encode()).hexdigest():
                    flash('Current password is incorrect.', 'danger')
                    return render_template('profile.html', form=form, today_date=date.today().isoformat())
                
                # Update password
                current_user.password = hashlib.sha256(form.new_password.data.encode()).hexdigest()
                flash('Password updated successfully.', 'success')
            elif form.current_password.data:
                # Verify current password for non-password changes
                if current_user.password != hashlib.sha256(form.current_password.data.encode()).hexdigest():
                    flash('Current password is incorrect.', 'danger')
                    return render_template('profile.html', form=form, today_date=date.today().isoformat())
            
            db.session.commit()
            flash('Profile updated successfully.', 'success')
            return redirect(url_for('profile'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Profile update error: {str(e)}')
            flash('An error occurred while updating your profile.', 'danger')
    
    return render_template('profile.html', form=form, today_date=date.today().isoformat())

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash('Cannot edit admin user.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    form = UserProfileForm(obj=user)
    if form.validate_on_submit():
        try:
            user.full_name = form.full_name.data
            user.qualification = form.qualification.data
            user.dob = form.dob.data
            
            if form.new_password.data:
                user.password = hashlib.sha256(form.new_password.data.encode()).hexdigest()
            
            db.session.commit()
            flash('User updated successfully.', 'success')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'User update error: {str(e)}')
            flash('An error occurred while updating the user.', 'danger')
    
    return render_template('edit_user.html', form=form, user=user, today_date=date.today().isoformat())

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash('Cannot delete admin user.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    try:
        # Delete all quiz attempts associated with this user
        QuizAttempt.query.filter_by(user_id=user_id).delete()
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'User deletion error: {str(e)}')
        flash('An error occurred while deleting the user.', 'danger')
    
    return redirect(url_for('admin_dashboard'))

@app.context_processor
def inject_user():
    return dict(current_user=current_user)

@app.errorhandler(404)
def not_found_error(error):
    app.logger.info(f'Page not found: {request.url}')
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(error):
    if app.config['SHOW_ERROR_DETAILS']:
        # If SHOW_ERROR_DETAILS is True, raise the error to see the details
        raise error
    return render_template('500.html'), 500

@app.errorhandler(Exception)
def unhandled_exception(error):
    app.logger.error(f'Unhandled Exception: {error}')
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Create argument parser
    parser = argparse.ArgumentParser(description='Run the Quiz Master application')
    parser.add_argument('--debug-errors', 
                       action='store_true',
                       help='Show detailed error messages instead of 500.html')
    
    args = parser.parse_args()
    
    # Set the configuration based on command line argument
    app.config['SHOW_ERROR_DETAILS'] = args.debug_errors
    
    # Create the database tables
    with app.app_context():
        db.create_all()
    
    app.run(debug=True)