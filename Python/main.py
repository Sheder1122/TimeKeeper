# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import secrets

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(32)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///time_tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    hours = db.Column(db.Float, nullable=False)
    project_name = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f'<Запись {self.employee_name} - {self.project_name} - {self.hours}ч>'

with app.app_context():
    db.create_all()

def validate_date(date_string):
    try:
        datetime.strptime(date_string, '%Y-%m-%d')
        return True
    except ValueError:
        return False

@app.route('/')
def index():
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    query = Record.query
    if date_from:
        query = query.filter(Record.date >= date_from)
    if date_to:
        query = query.filter(Record.date <= date_to)

    records = query.order_by(Record.date.desc()).all()
    return render_template('index.html',
                           records=records,
                           date_from=date_from,
                           date_to=date_to)

@app.route('/add', methods=['GET', 'POST'])
def add_record():
    if request.method == 'POST':
        name = request.form.get('employee_name', '').strip()
        date = request.form.get('date', '')
        hours_str = request.form.get('hours', '')
        project = request.form.get('project_name', '').strip()

        error = None
        if not name:
            error = 'Имя сотрудника обязательно'
        elif not date:
            error = 'Дата обязательна'
        elif not validate_date(date):
            error = 'Неверный формат даты (нужно ГГГГ-ММ-ДД)'
        elif not hours_str:
            error = 'Часы обязательны'
        else:
            try:
                hours = float(hours_str)
                if hours <= 0:
                    error = 'Часы должны быть больше нуля'
            except ValueError:
                error = 'Часы должны быть числом (например 2.5)'

        if not project:
            error = 'Название проекта обязательно'

        if error:
            flash(error, 'danger')
        else:
            new_record = Record(
                employee_name=name,
                date=date,
                hours=hours,
                project_name=project
            )
            db.session.add(new_record)
            db.session.commit()
            flash('Запись успешно добавлена!', 'success')
            return redirect(url_for('index'))

    return render_template('add_edit.html', title='Добавить запись', record=None)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_record(id):
    record = Record.query.get_or_404(id)

    if request.method == 'POST':
        name = request.form.get('employee_name', '').strip()
        date = request.form.get('date', '')
        hours_str = request.form.get('hours', '')
        project = request.form.get('project_name', '').strip()

        error = None
        if not name:
            error = 'Имя сотрудника обязательно'
        elif not date:
            error = 'Дата обязательна'
        elif not validate_date(date):
            error = 'Неверный формат даты'
        elif not hours_str:
            error = 'Часы обязательны'
        else:
            try:
                hours = float(hours_str)
                if hours <= 0:
                    error = 'Часы должны быть больше нуля'
            except ValueError:
                error = 'Часы должны быть числом'

        if not project:
            error = 'Название проекта обязательно'

        if error:
            flash(error, 'danger')
        else:
            record.employee_name = name
            record.date = date
            record.hours = hours
            record.project_name = project
            db.session.commit()
            flash('Запись обновлена!', 'success')
            return redirect(url_for('index'))

    return render_template('add_edit.html', title='Редактировать запись', record=record)

@app.route('/delete/<int:id>', methods=['POST'])
def delete_record(id):
    record = Record.query.get_or_404(id)
    db.session.delete(record)
    db.session.commit()
    flash('Запись удалена', 'success')
    return redirect(url_for('index'))

@app.route('/report/employee', methods=['GET', 'POST'])
def report_employee():
    employees_rows = db.session.query(Record.employee_name).distinct().all()
    employees = [row[0] for row in employees_rows]

    report_data = None
    selected_employee = ''
    date_from = ''
    date_to = ''

    if request.method == 'POST':
        selected_employee = request.form.get('employee_name', '')
        date_from = request.form.get('date_from', '')
        date_to = request.form.get('date_to', '')

        if selected_employee:
            query = Record.query.filter_by(employee_name=selected_employee)
            if date_from:
                query = query.filter(Record.date >= date_from)
            if date_to:
                query = query.filter(Record.date <= date_to)

            total = 0.0
            projects_dict = {}
            for record in query.all():
                total += record.hours
                projects_dict[record.project_name] = projects_dict.get(record.project_name, 0) + record.hours

            projects_list = [(proj, hours) for proj, hours in projects_dict.items()]
            report_data = {
                'total_hours': total,
                'projects': projects_list
            }

    return render_template('report_employee.html',
                           employees=employees,
                           report_data=report_data,
                           selected_employee=selected_employee,
                           date_from=date_from,
                           date_to=date_to)

@app.route('/report/project', methods=['GET', 'POST'])
def report_project():
    projects_rows = db.session.query(Record.project_name).distinct().all()
    projects = [row[0] for row in projects_rows]

    report_data = None
    selected_project = ''

    if request.method == 'POST':
        selected_project = request.form.get('project_name', '')
        if selected_project:
            records = Record.query.filter_by(project_name=selected_project).all()

            total = 0.0
            employees_dict = {}
            for record in records:
                total += record.hours
                employees_dict[record.employee_name] = employees_dict.get(record.employee_name, 0) + record.hours

            employees_list = [(emp, hours) for emp, hours in employees_dict.items()]
            report_data = {
                'total_hours': total,
                'employees': employees_list
            }

    return render_template('report_project.html',
                           projects=projects,
                           report_data=report_data,
                           selected_project=selected_project)

if __name__ == '__main__':
    app.run(debug=True)