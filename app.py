from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import json
from fpdf import FPDF
import os
import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change to a real secret key

# User roles
ROLES = {
    'unverified': 1,
    'verified': 2,
    'admin': 3
}

# Example user data
user_data = {
    'admin': {
        'password': generate_password_hash('admin'),
        'name': 'Administrator',
        'role': ROLES['admin']
    }
}

# Load questions from JSON file
def load_questions(subject, grade):
    path = os.path.join('questions', subject, grade, 'questions.json')
    with open(path, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    return questions

# Custom PDF class with footer
class CustomPDF(FPDF):
    def footer(self):
        self.set_y(-20)
        self.set_x(0)
        self.set_font('DejaVu', 'I', 8)
        line_width = self.w + 2 * self.l_margin
        self.cell(line_width, 0, '      ______________________________________________________________________________________________________________________________', 0, 1, 'L')
        self.set_y(-15)
        self.set_font('DejaVu', 'I', 10)
        self.cell(0, 10, 'Copyright by Mateusz Kowalczyk', 0, 0, 'C')

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']

        if login in user_data and check_password_hash(user_data[login]['password'], password):
            session['user'] = login
            session['user_name'] = user_data[login]['name']
            return redirect(url_for('select_subject_and_grade'))
        else:
            flash('Invalid login or password!', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('user_name', None)
    return redirect(url_for('login'))

def check_access(required_role, subject=None, grade=None):
    if 'user' not in session:
        return redirect(url_for('login'))

    user = user_data.get(session['user'], {})
    user_role = user.get('role', 0)
    
    if user_role < required_role:
        return redirect(url_for('no_access'))

    if subject and grade:
        permissions = user.get('permissions', {})
        allowed_subjects = permissions.get('subjects', [])
        allowed_grades = permissions.get('grades', [])
        
        if subject not in allowed_subjects or grade not in allowed_grades:
            return redirect(url_for('no_access'))

    return None


def flatten_questions(questions):
    flattened_questions = []
    for question in questions:
        for version in question['versions']:
            flattened_questions.append({
                'id': question['id'],
                'author': question['author'],
                'points': question['points'],
                'time': question['time'],
                'question_text': version['question_text'],
                'options': version['options'],
                'answer': version['answer'],
                'version': version['version']
            })
    return flattened_questions
    
@app.route('/main')
def index():
    # Check user access and permissions
    access_check = check_access(ROLES['verified'], subject=session.get('subject'), grade=session.get('grade'))
    if access_check:
        return access_check

    subject = session.get('subject')
    grade = session.get('grade')
    if not subject or not grade:
        return redirect(url_for('select_subject_and_grade'))

    questions = load_questions(subject, grade)
    flattened_questions = flatten_questions(questions)

    return render_template('index.html', questions=flattened_questions, user_name=session['user'])



    # Logic to get and process questions
    questions = load_questions()
    flattened_questions = flatten_questions(questions)
    
    return render_template('index.html', questions=flattened_questions, user_name=session['user'])

    questions = load_questions()
    flattened_questions = []
    for question in questions:
        for version in question['versions']:
            flattened_questions.append({
                'id': question['id'],
                'author': question['author'],
                'points': question['points'],
                'time': question['time'],
                'question_text': version['question_text'],
                'options': version['options'],
                'answer': version['answer'],
                'version': version['version']
            })
    return render_template('index.html', questions=flattened_questions, user_name=session.get('user_name'))

@app.route('/select_fields', methods=['POST'])
def select_fields():
    selected_questions = request.form.getlist('selected_question')
    return render_template('select_fields.html', selected_questions=selected_questions)

# Helper function to wrap text
def wrap_text(pdf, text, max_width):
    pdf.set_font("DejaVu", size=12)
    lines = []
    words = text.split(' ')
    
    line = ''
    for word in words:
        test_line = f'{line} {word}'.strip()
        if pdf.get_string_width(test_line) > max_width:
            lines.append(line)
            line = word
        else:
            line = test_line
    lines.append(line)
    
    return lines

# Route to generate the quiz PDF
@app.route('/generate', methods=['POST'])
@app.route('/generate', methods=['POST'])
def generate():
    # Pobierz subject i grade z sesji
    subject = session.get('subject')
    grade = session.get('grade')
    
    # Sprawdź, czy subject i grade są ustawione
    if not subject or not grade:
        flash('Subject and grade must be selected!', 'error')
        return redirect(url_for('select_subject_and_grade'))

    # Wczytaj pytania
    questions = load_questions(subject, grade)
    
    # Pozostała część funkcji
    selected_question_ids = request.form.getlist('selected_question')
    
    selected_questions = []
    for question in questions:
        if str(question['id']) in selected_question_ids:
            for version in question['versions']:
                if version['version'] == 'A':
                    selected_questions.append({
                        'id': question['id'],
                        'author': question['author'],
                        'points': question['points'],
                        'time': question['time'],
                        'question_text': version['question_text'],
                        'options': version['options'],
                        'answer': version['answer'],
                        'version': version['version']
                    })
                    
    name_field = 'name' in request.form
    date_field = 'date' in request.form
    hide_points = 'hide_points' in request.form
    hide_total_points = 'hide_total_points' in request.form

    pdf = CustomPDF()
    pdf.add_font('DejaVu', '', 'fonts/DejaVuSans.ttf', uni=True)
    pdf.add_font('DejaVu', 'B', 'fonts/DejaVuSans-Bold.ttf', uni=True)
    pdf.add_font('DejaVu', 'I', 'fonts/DejaVuSans-Oblique.ttf', uni=True)
    pdf.add_font('DejaVu', 'BI', 'fonts/DejaVuSans-BoldOblique.ttf', uni=True)
    pdf.set_auto_page_break(auto=True, margin=15)

    questions_data = {'A': []}
    total_points = {'A': 0}

    for question in selected_questions:
        author = question['author']
        points = question['points']
        time = question['time']
        version = question['version']
        total_points[version] += points
        questions_data[version].append((
            question['question_text'], question['options'], points, author, time, version, question['answer']
        ))

    def add_questions_to_pdf(group, questions_data):
        pdf.add_page()
        pdf.set_font("DejaVu", size=12)
        pdf.cell(0, 10, f'Group {group}:', 0, 1)

        if name_field or date_field:
            pdf.set_font("DejaVu", size=12)
            pdf.ln(5)  # Reduce the space here

            pdf.set_x(pdf.l_margin)
            name_text = 'Name .........................................................................'
            date_text = f'Date _________ {datetime.datetime.now().year}'
            
            name_width = pdf.get_string_width(name_text)
            date_width = pdf.get_string_width(date_text)
            
            total_width = pdf.w - 2 * pdf.r_margin
            name_position = pdf.l_margin
            date_position = total_width - date_width - pdf.r_margin
            
            pdf.set_x(name_position)
            pdf.cell(name_width, 10, name_text, 0, 0)
            pdf.set_x(date_position)
            pdf.cell(date_width, 10, date_text, 0, 1)

        pdf.ln(5)  # Reduce the space here as well

        if not hide_total_points:
            total_points_text = f'Total Points: {total_points[group]}'
            pdf.set_x(pdf.l_margin)
            pdf.cell(0, 10, total_points_text, 0, 1)

        pdf.ln(5)  # Reduce the space here as well

        question_number = 1
        for question_text, options, points, author, time, version, answer in questions_data:
            pdf.set_font("DejaVu", size=12)
            pdf.set_x(pdf.l_margin)

            page_width = pdf.w - 2 * pdf.r_margin
            wrapped_question_lines = wrap_text(pdf, question_text, page_width)
            
            pdf.cell(0, 10, f'{question_number}. {wrapped_question_lines[0]}', ln=True)

            for line in wrapped_question_lines[1:]:
                pdf.cell(0, 10, line, ln=True)
            
            if not hide_points:
                num_dots = 13
                dots_text = '.' * num_dots
                dots_needed = num_dots - 5
                points_text = f"({dots_text[:dots_needed]}/{points})"

                question_width = pdf.get_string_width(wrapped_question_lines[0])
                points_x_position = pdf.w - pdf.r_margin - pdf.get_string_width(points_text)

                pdf.set_x(points_x_position)
                pdf.cell(0, 10, points_text, ln=True)

            pdf.set_font("DejaVu", size=10)
            pdf.ln(5)

            left_margin = pdf.l_margin
            right_margin = pdf.r_margin
            page_width = pdf.w - left_margin - right_margin
            options_text = [f'{chr(65 + i)}. {option}' for i, option in enumerate(options)]

            total_options_width = sum(pdf.get_string_width(option) for option in options_text)
            spacing_needed = (page_width - total_options_width) / (len(options_text) + 1)

            current_x = left_margin
            for option in options_text:
                pdf.set_x(current_x)
                pdf.cell(pdf.get_string_width(option), 10, option, ln=False)
                current_x += pdf.get_string_width(option) + spacing_needed

            pdf.ln(10)
            question_number += 1

    add_questions_to_pdf('A', questions_data['A'])
    quiz_pdf_path = 'static/quiz.pdf'
    pdf.output(quiz_pdf_path)

    # Generate answer key PDF
    generate_answer_key(selected_question_ids)
    
    return redirect(url_for('download_files_page'))

def generate_answer_key(selected_question_ids):
    # Pobierz subject i grade z sesji
    subject = session.get('subject')
    grade = session.get('grade')
    
    # Sprawdź, czy subject i grade są ustawione
    if not subject or not grade:
        flash('Subject and grade must be selected!', 'error')
        return

    # Wczytaj pytania
    questions = load_questions(subject, grade)
    
    # Generowanie klucza odpowiedzi
    pdf = CustomPDF()
    pdf.add_font('DejaVu', '', 'fonts/DejaVuSans.ttf', uni=True)
    pdf.add_font('DejaVu', 'B', 'fonts/DejaVuSans-Bold.ttf', uni=True)
    pdf.add_font('DejaVu', 'I', 'fonts/DejaVuSans-Oblique.ttf', uni=True)
    pdf.add_font('DejaVu', 'BI', 'fonts/DejaVuSans-BoldOblique.ttf', uni=True)
    pdf.set_auto_page_break(auto=True, margin=15)
    
    pdf.add_page()
    pdf.set_font("DejaVu", size=12)
    pdf.cell(0, 10, 'Answer Key', 0, 1)
    
    for question in questions:
        if str(question['id']) in selected_question_ids:
            for version in question['versions']:
                if version['version'] == 'A':
                    pdf.cell(0, 10, f'Question {question["id"]} Answer: {version["answer"]}', 0, 1)
    
    answer_key_pdf_path = 'static/answer_key.pdf'
    pdf.output(answer_key_pdf_path)


@app.route('/download_files_page')
def download_files_page():
    return render_template('download.html')

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory('static', filename)
    
@app.route('/no_access')
def no_access():
    return render_template('no_access.html')

    
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    access_check = check_access(ROLES['admin'])
    if access_check:
        return access_check

    if request.method == 'POST':
        login = request.form['login']
        if 'create_user' in request.form:
            password = request.form['password']
            name = request.form['name']
            role = int(request.form['role'])
            permissions = {
                'subjects': request.form.getlist('subjects'),
                'grades': request.form.getlist('grades')
            }
            if login in user_data:
                flash('User already exists!', 'error')
            else:
                user_data[login] = {
                    'password': generate_password_hash(password),
                    'name': name,
                    'role': role,
                    'permissions': permissions
                }
                flash('User created successfully!', 'success')
        elif 'update_permissions' in request.form:
            permissions = {
                'subjects': request.form.getlist('subjects'),
                'grades': request.form.getlist('grades')
            }
            if login in user_data:
                user_data[login]['permissions'] = permissions
                flash('User permissions updated successfully!', 'success')
            else:
                flash('User does not exist!', 'error')

    users = list(user_data.keys())
    subjects = ['matematyka', 'fizyka']
    grades = ['klasa1', 'klasa2']
    return render_template('admin.html', users=users, subjects=subjects, grades=grades)

    users = list(user_data.keys())
    subjects = ['matematyka', 'fizyka']  # Przykładowa lista przedmiotów
    grades = ['klasa1', 'klasa2']  # Przykładowa lista klas
    return render_template('admin.html', users=users, subjects=subjects, grades=grades)
    
@app.route('/select_subject_and_grade', methods=['GET', 'POST'])
def select_subject_and_grade():
    if request.method == 'POST':
        subject = request.form['subject']
        grade = request.form['grade']
        session['subject'] = subject
        session['grade'] = grade
        return redirect(url_for('index'))
    return render_template('select_subject_and_grade.html')


if __name__ == '__main__':
    app.run(debug=True)
