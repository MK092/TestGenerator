from flask import Flask, render_template, request, send_from_directory
import json
from fpdf import FPDF
import os
import datetime

app = Flask(__name__)

# Load questions from JSON file
def load_questions():
    with open('questions.json', 'r', encoding='utf-8') as f:
        questions = json.load(f)
    return questions

# Custom PDF class with footer
class CustomPDF(FPDF):
    def footer(self):
        # Set the Y position to be 20 units from the bottom of the page
        self.set_y(-20)
        
        # Draw a line across the entire width of the page (including margins)
        self.set_x(0)
        self.set_font('DejaVu', 'I', 8)
        line_width = self.w + 2 * self.l_margin  # Page width plus margins
        self.cell(line_width, 0, '      ______________________________________________________________________________________________________________________________', 0, 1, 'L')
        
        # Set font for the footer text
        self.set_y(-15)
        self.set_font('DejaVu', 'I', 10)
        # Footer text
        self.cell(0, 10, 'Copyright by Mateusz Kowalczyk', 0, 0, 'C')

# Home route to display the description and login button
@app.route('/')
def home():
    return render_template('home.html')

# Main route to display the form and preview questions
@app.route('/main')
def main():
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
    return render_template('index.html', questions=flattened_questions)

# Route to select additional fields
@app.route('/select_fields', methods=['POST'])
def select_fields():
    selected_questions = request.form.getlist('question')
    return render_template('select_fields.html', selected_questions=selected_questions)

# Helper function to wrap text
def wrap_text(pdf, text, max_width):
    """ Wrap text to fit within a given width. """
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

# Route to generate the PDFs
@app.route('/generate', methods=['POST'])
def generate():
    questions = load_questions()
    selected_questions = request.form.getlist('selected_question')
    name_field = 'name' in request.form
    date_field = 'date' in request.form
    hide_points = 'hide_points' in request.form
    hide_total_points = 'hide_total_points' in request.form

    pdf = CustomPDF()  # Use the custom PDF class
    pdf.add_font('DejaVu', '', 'fonts/DejaVuSans.ttf', uni=True)
    pdf.add_font('DejaVu', 'B', 'fonts/DejaVuSans-Bold.ttf', uni=True)
    pdf.add_font('DejaVu', 'I', 'fonts/DejaVuSans-Oblique.ttf', uni=True)
    pdf.add_font('DejaVu', 'BI', 'fonts/DejaVuSans-BoldOblique.ttf', uni=True)
    pdf.set_auto_page_break(auto=True, margin=15)

    answer_key_pdf = CustomPDF()  # Use the custom PDF class for answer key as well
    answer_key_pdf.add_font('DejaVu', '', 'fonts/DejaVuSans.ttf', uni=True)
    answer_key_pdf.add_font('DejaVu', 'B', 'fonts/DejaVuSans-Bold.ttf', uni=True)
    answer_key_pdf.add_font('DejaVu', 'I', 'fonts/DejaVuSans-Oblique.ttf', uni=True)
    answer_key_pdf.add_font('DejaVu', 'BI', 'fonts/DejaVuSans-BoldOblique.ttf', uni=True)
    answer_key_pdf.set_auto_page_break(auto=True, margin=15)

    total_points = {'A': 0}
    questions_data = {'A': []}

    for question in questions:
        author = question['author']
        points = question['points']
        time = question['time']
        for version in question['versions']:
            if version['version'] == 'A':
                version_letter = version['version']
                total_points[version_letter] += points
                questions_data[version_letter].append((
                    version['question_text'], version['options'], points, author, time, version_letter, version['answer']
                ))

    def add_questions_to_pdf(group, questions_data):
        pdf.add_page()
        pdf.set_font("DejaVu", size=12)
        pdf.cell(0, 10, f'Group {group}:', 0, 1)

        if name_field or date_field:
            pdf.set_font("DejaVu", size=12)
            pdf.ln(5)  # Small line break before Name and Date

            # Print Name and Date fields on the same line
            pdf.set_x(pdf.l_margin)  # Start at the left margin
            name_text = 'Name .........................................................................'
            date_text = f'Date _________ {datetime.datetime.now().year}'
            
            # Calculate the maximum width for Name and Date fields
            name_width = pdf.get_string_width(name_text)
            date_width = pdf.get_string_width(date_text)
            
            # Calculate positions
            total_width = pdf.w - 2 * pdf.r_margin
            name_position = pdf.l_margin
            date_position = total_width - date_width - pdf.r_margin
            
            pdf.set_x(name_position)
            pdf.cell(name_width, 10, name_text, 0, 0)  # Print Name field
            pdf.set_x(date_position)
            pdf.cell(date_width, 10, date_text, 0, 1)  # Print Date field

        pdf.ln(5)

        if not hide_total_points:
            total_points_text = f'Total Points: {total_points[group]}'
            pdf.set_x(pdf.l_margin)
            pdf.cell(0, 10, total_points_text, 0, 1)

        pdf.ln(10)

        # Add questions with numbering
        question_number = 1
        for question_text, options, points, author, time, version, answer in questions_data:
            pdf.set_font("DejaVu", size=12)
            pdf.set_x(pdf.l_margin)  # Reset X position to left margin

            # Use wrap_text to handle question text
            page_width = pdf.w - 2 * pdf.r_margin
            wrapped_question_lines = wrap_text(pdf, question_text, page_width)
            
            # Print the first line with numbering
            pdf.cell(0, 10, f'{question_number}. {wrapped_question_lines[0]}', ln=True)

            # Print all but the first line without numbering
            for line in wrapped_question_lines[1:]:
                pdf.cell(0, 10, line, ln=True)
            
            if not hide_points:
                # Handle the last line with points
                num_dots = 13
                dots_text = '.' * num_dots
                dots_needed = num_dots - 5
                points_text = f"({dots_text[:dots_needed]}/{points})"

                # Calculate X position for the points text
                question_width = pdf.get_string_width(wrapped_question_lines[0])
                points_x_position = pdf.w - pdf.r_margin - pdf.get_string_width(points_text)

                # Print the last line with points
                pdf.set_x(points_x_position)
                pdf.cell(0, 10, points_text, ln=True)

            # Format options to fit in one line
            pdf.set_font("DejaVu", size=10)
            pdf.ln(2)  # Small line break before options

            left_margin = pdf.l_margin
            right_margin = pdf.r_margin + 20  # Increase right margin for additional space
            page_width = pdf.w - left_margin - right_margin  # Width minus margins
            option_labels = ['A', 'B', 'C', 'D']
            options_text = [f"{option_labels[i]}. {option}" for i, option in enumerate(options)]

            # Calculate width of all options and spacing needed
            total_text_width = sum(pdf.get_string_width(opt) for opt in options_text)
            num_spaces = len(options_text) - 1
            space_between_options = (page_width - total_text_width) / num_spaces

            # Print each option with calculated spacing
            for i, option in enumerate(options_text):
                pdf.cell(pdf.get_string_width(option), 10, option)
                if i != len(options_text) - 1:  # Add space after every option except the last one
                    pdf.cell(space_between_options, 10, '')

            pdf.ln(10)  # Space after options
            question_number += 1

    # Add questions for each group to the PDF
    add_questions_to_pdf('A', questions_data['A'])

    def add_answer_key_to_pdf(group, questions_data):
        answer_key_pdf.add_page()
        answer_key_pdf.set_font("DejaVu", size=12)
        answer_key_pdf.cell(0, 10, f'Answer Key Group {group}:', 0, 1)
        answer_key_pdf.ln(10)

        # Add answers with numbering
        question_number = 1
        for question_text, options, points, author, time, version, answer in questions_data:
            answer_key_pdf.set_font("DejaVu", size=12)
            answer_key_pdf.cell(0, 10, f'{question_number}. {question_text} - Answer: {answer}', 0, 1)
            question_number += 1

    # Add answer keys to the PDF
    add_answer_key_to_pdf('A', questions_data['A'])

    pdf.output('generated_test.pdf')
    answer_key_pdf.output('answer_key.pdf')

    return '''
    <h1>PDFs Generated Successfully</h1>
    <a href="/download/generated_test.pdf">Download Generated Test</a><br>
    <a href="/download/answer_key.pdf">Download Answer Key</a>
    '''

# Route to download files
@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory('.', filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
