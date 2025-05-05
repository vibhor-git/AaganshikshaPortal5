from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, Response
from flask_login import login_required, current_user
from models import User, Center, Inventory, NutritionTip, Activity, Student, Attendance, Complaint
from forms import UserForm, EditUserForm, CenterForm, InventoryForm, NutritionTipForm, ActivityForm, ReportForm
from app import db
from datetime import datetime
from functools import wraps
import csv
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

admin_bp = Blueprint('admin', __name__)

# Admin access decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('You need to be an admin to access this page.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # Count statistics for dashboard
    users_count = User.query.count()
    centers_count = Center.query.count()
    students_count = Student.query.count()
    inventory_count = Inventory.query.count()
    tips_count = NutritionTip.query.count()
    activities_count = Activity.query.count()
    complaints_count = Complaint.query.filter_by(status='pending').count()

    # Get recent activities and nutrition tips
    recent_activities = Activity.query.order_by(Activity.created_at.desc()).limit(5).all()
    recent_tips = NutritionTip.query.order_by(NutritionTip.created_at.desc()).limit(5).all()

    return render_template('admin/dashboard.html', 
                           users_count=users_count,
                           centers_count=centers_count,
                           students_count=students_count,
                           inventory_count=inventory_count,
                           tips_count=tips_count,
                           activities_count=activities_count,
                           complaints_count=complaints_count,
                           recent_activities=recent_activities,
                           recent_tips=recent_tips)

# Users Management
@admin_bp.route('/users')
@login_required
@admin_required
def users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    form = UserForm()

    # Populate center choices
    form.center_id.choices = [(0, 'None')] + [(c.id, c.name) for c in Center.query.all()]

    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            role=form.role.data,
            aadhar_number=form.aadhar_number.data
        )
        user.set_password(form.password.data)

        # Set center_id only if the role is teacher and a center was selected
        if form.role.data == 'teacher' and form.center_id.data != 0:
            user.center_id = form.center_id.data

        db.session.add(user)
        db.session.commit()

        flash('User added successfully!', 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/users.html', form=form, is_add=True)

@admin_bp.route('/users/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(id):
    user = User.query.get_or_404(id)
    form = EditUserForm(original_username=user.username, original_email=user.email)

    # Populate center choices
    form.center_id.choices = [(0, 'None')] + [(c.id, c.name) for c in Center.query.all()]

    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.role = form.role.data
        user.aadhar_number = form.aadhar_number.data

        # Set center_id based on role and selection
        if form.role.data == 'teacher' and form.center_id.data != 0:
            user.center_id = form.center_id.data
        else:
            user.center_id = None

        if form.password.data:
            user.set_password(form.password.data)

        db.session.commit()
        flash('User updated successfully!', 'success')
        return redirect(url_for('admin.users'))

    elif request.method == 'GET':
        form.username.data = user.username
        form.email.data = user.email
        form.role.data = user.role
        form.aadhar_number.data = user.aadhar_number
        form.center_id.data = user.center_id or 0

    return render_template('admin/users.html', form=form, user=user, is_edit=True)

@admin_bp.route('/users/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_user(id):
    user = User.query.get_or_404(id)

    # Prevent deleting yourself
    if user.id == current_user.id:
        flash('You cannot delete your own account!', 'danger')
        return redirect(url_for('admin.users'))

    db.session.delete(user)
    db.session.commit()

    flash('User deleted successfully!', 'success')
    return redirect(url_for('admin.users'))

# Centers Management
@admin_bp.route('/centers')
@login_required
@admin_required
def centers():
    centers = Center.query.all()
    return render_template('admin/centers.html', centers=centers)

@admin_bp.route('/centers/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_center():
    form = CenterForm()

    if form.validate_on_submit():
        center = Center(
            name=form.name.data,
            address=form.address.data,
            contact_number=form.contact_number.data,
            email=form.email.data
        )

        db.session.add(center)
        db.session.commit()

        flash('Center added successfully!', 'success')
        return redirect(url_for('admin.centers'))

    return render_template('admin/centers.html', form=form, is_add=True)

@admin_bp.route('/centers/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_center(id):
    center = Center.query.get_or_404(id)
    form = CenterForm()

    if form.validate_on_submit():
        center.name = form.name.data
        center.address = form.address.data
        center.contact_number = form.contact_number.data
        center.email = form.email.data

        db.session.commit()
        flash('Center updated successfully!', 'success')
        return redirect(url_for('admin.centers'))

    elif request.method == 'GET':
        form.name.data = center.name
        form.address.data = center.address
        form.contact_number.data = center.contact_number
        form.email.data = center.email

    return render_template('admin/centers.html', form=form, center=center, is_edit=True)

@admin_bp.route('/centers/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_center(id):
    center = Center.query.get_or_404(id)

    # Check if center has associated students or inventory
    if center.students or center.inventory_items:
        flash('Cannot delete center that has associated students or inventory!', 'danger')
        return redirect(url_for('admin.centers'))

    db.session.delete(center)
    db.session.commit()

    flash('Center deleted successfully!', 'success')
    return redirect(url_for('admin.centers'))

# Inventory Management
@admin_bp.route('/inventory')
@login_required
@admin_required
def inventory():
    inventory_items = Inventory.query.all()
    return render_template('admin/inventory.html', inventory_items=inventory_items)

@admin_bp.route('/inventory/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_inventory():
    form = InventoryForm()

    # Populate center choices
    form.center_id.choices = [(c.id, c.name) for c in Center.query.all()]

    if form.validate_on_submit():
        inventory = Inventory(
            item_name=form.item_name.data,
            quantity=form.quantity.data,
            unit=form.unit.data,
            description=form.description.data,
            center_id=form.center_id.data
        )

        db.session.add(inventory)
        db.session.commit()

        flash('Inventory item added successfully!', 'success')
        return redirect(url_for('admin.inventory'))

    return render_template('admin/inventory.html', form=form, is_add=True)

@admin_bp.route('/inventory/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_inventory(id):
    inventory = Inventory.query.get_or_404(id)
    form = InventoryForm()

    # Populate center choices
    form.center_id.choices = [(c.id, c.name) for c in Center.query.all()]

    if form.validate_on_submit():
        inventory.item_name = form.item_name.data
        inventory.quantity = form.quantity.data
        inventory.unit = form.unit.data
        inventory.description = form.description.data
        inventory.center_id = form.center_id.data
        inventory.updated_at = datetime.utcnow()

        db.session.commit()
        flash('Inventory item updated successfully!', 'success')
        return redirect(url_for('admin.inventory'))

    elif request.method == 'GET':
        form.item_name.data = inventory.item_name
        form.quantity.data = inventory.quantity
        form.unit.data = inventory.unit
        form.description.data = inventory.description
        form.center_id.data = inventory.center_id

    return render_template('admin/inventory.html', form=form, inventory=inventory, is_edit=True)

@admin_bp.route('/inventory/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_inventory(id):
    inventory = Inventory.query.get_or_404(id)

    db.session.delete(inventory)
    db.session.commit()

    flash('Inventory item deleted successfully!', 'success')
    return redirect(url_for('admin.inventory'))

# Nutrition Tips Management
@admin_bp.route('/nutrition')
@login_required
@admin_required
def nutrition():
    nutrition_tips = NutritionTip.query.all()
    return render_template('admin/nutrition.html', nutrition_tips=nutrition_tips)

@admin_bp.route('/nutrition/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_nutrition():
    form = NutritionTipForm()

    if form.validate_on_submit():
        nutrition_tip = NutritionTip(
            title=form.title.data,
            content=form.content.data,
            is_active=form.is_active.data,
            user_id=current_user.id
        )

        db.session.add(nutrition_tip)
        db.session.commit()

        flash('Nutrition tip added successfully!', 'success')
        return redirect(url_for('admin.nutrition'))

    return render_template('admin/nutrition.html', form=form, is_add=True)

@admin_bp.route('/nutrition/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_nutrition(id):
    nutrition_tip = NutritionTip.query.get_or_404(id)
    form = NutritionTipForm()

    if form.validate_on_submit():
        nutrition_tip.title = form.title.data
        nutrition_tip.content = form.content.data
        nutrition_tip.is_active = form.is_active.data
        nutrition_tip.updated_at = datetime.utcnow()

        db.session.commit()
        flash('Nutrition tip updated successfully!', 'success')
        return redirect(url_for('admin.nutrition'))

    elif request.method == 'GET':
        form.title.data = nutrition_tip.title
        form.content.data = nutrition_tip.content
        form.is_active.data = nutrition_tip.is_active

    return render_template('admin/nutrition.html', form=form, nutrition_tip=nutrition_tip, is_edit=True)

@admin_bp.route('/nutrition/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_nutrition(id):
    nutrition_tip = NutritionTip.query.get_or_404(id)

    db.session.delete(nutrition_tip)
    db.session.commit()

    flash('Nutrition tip deleted successfully!', 'success')
    return redirect(url_for('admin.nutrition'))

# Activities Management
@admin_bp.route('/activities')
@login_required
@admin_required
def activities():
    activities = Activity.query.all()
    return render_template('admin/activities.html', activities=activities)

@admin_bp.route('/activities/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_activity():
    form = ActivityForm()

    if form.validate_on_submit():
        activity = Activity(
            title=form.title.data,
            description=form.description.data,
            date=form.date.data,
            is_active=form.is_active.data,
            user_id=current_user.id
        )

        db.session.add(activity)
        db.session.commit()

        flash('Activity added successfully!', 'success')
        return redirect(url_for('admin.activities'))

    return render_template('admin/activities.html', form=form, is_add=True)

@admin_bp.route('/activities/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_activity(id):
    activity = Activity.query.get_or_404(id)
    form = ActivityForm()

    if form.validate_on_submit():
        activity.title = form.title.data
        activity.description = form.description.data
        activity.date = form.date.data
        activity.is_active = form.is_active.data
        activity.updated_at = datetime.utcnow()

        db.session.commit()
        flash('Activity updated successfully!', 'success')
        return redirect(url_for('admin.activities'))

    elif request.method == 'GET':
        form.title.data = activity.title
        form.description.data = activity.description
        form.date.data = activity.date
        form.is_active.data = activity.is_active

    return render_template('admin/activities.html', form=form, activity=activity, is_edit=True)

@admin_bp.route('/activities/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_activity(id):
    activity = Activity.query.get_or_404(id)

    db.session.delete(activity)
    db.session.commit()

    flash('Activity deleted successfully!', 'success')
    return redirect(url_for('admin.activities'))

# Reports Management
@admin_bp.route('/reports', methods=['GET', 'POST'])
@login_required
@admin_required
def reports():
    form = ReportForm()

    # Populate center choices
    center_choices = [(0, 'All Centers')] + [(c.id, c.name) for c in Center.query.all()]
    form.center_id.choices = center_choices

    if form.validate_on_submit():
        report_type = form.report_type.data
        center_id = form.center_id.data
        start_date = form.start_date.data
        end_date = form.end_date.data

        # Generate report based on selection
        if report_type == 'attendance':
            return generate_attendance_report(center_id, start_date, end_date)
        elif report_type == 'students':
            return generate_students_report(center_id)
        elif report_type == 'inventory':
            return generate_inventory_report(center_id)
        elif report_type == 'activities':
            return generate_activities_report(start_date, end_date)

    return render_template('admin/reports.html', form=form)

def generate_attendance_report(center_id, start_date, end_date):
    # Query for attendance data
    query = db.session.query(
        Student.name.label('student_name'),
        Center.name.label('center_name'),
        Attendance.date,
        Attendance.status,
        User.username.label('marked_by')
    ).join(Student, Attendance.student_id == Student.id
    ).join(Center, Student.center_id == Center.id
    ).join(User, Attendance.marked_by == User.id)

    if center_id != 0:  # Not 'All Centers'
        query = query.filter(Student.center_id == center_id)

    if start_date:
        query = query.filter(Attendance.date >= start_date)

    if end_date:
        query = query.filter(Attendance.date <= end_date)

    # Order by date and student name
    attendance_data = query.order_by(Attendance.date, Student.name).all()

    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(['Student Name', 'Center', 'Date', 'Status', 'Marked By'])

    # Write data
    for record in attendance_data:
        writer.writerow([
            record.student_name,
            record.center_name,
            record.date.strftime('%Y-%m-%d'),
            record.status,
            record.marked_by
        ])

    # Prepare response
    output.seek(0)
    filename = f'attendance_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

def generate_students_report(center_id):
    # Query for student data
    query = db.session.query(
        Student.name,
        Student.age,
        Student.gender,
        Student.parent_name,
        Student.parent_contact,
        Student.address,
        Student.enrollment_date,
        Center.name.label('center_name')
    ).join(Center, Student.center_id == Center.id)

    if center_id != 0:  # Not 'All Centers'
        query = query.filter(Student.center_id == center_id)

    # Order by center and student name
    student_data = query.order_by(Center.name, Student.name).all()

    # Create PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    # Create table data
    data = [['Name', 'Age', 'Gender', 'Parent Name', 'Parent Contact', 'Address', 'Enrollment Date', 'Center']]

    for student in student_data:
        data.append([
            student.name,
            str(student.age),
            student.gender,
            student.parent_name,
            student.parent_contact,
            student.address,
            student.enrollment_date.strftime('%Y-%m-%d') if student.enrollment_date else 'N/A',
            student.center_name
        ])

    # Create table
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    elements.append(table)
    doc.build(elements)

    buffer.seek(0)
    filename = f'students_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'

    return Response(
        buffer.getvalue(),
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

def generate_inventory_report(center_id):
    # Query for inventory data
    query = db.session.query(
        Inventory.item_name,
        Inventory.quantity,
        Inventory.unit,
        Inventory.description,
        Center.name.label('center_name')
    ).join(Center, Inventory.center_id == Center.id)

    if center_id != 0:  # Not 'All Centers'
        query = query.filter(Inventory.center_id == center_id)

    # Order by center and item name
    inventory_data = query.order_by(Center.name, Inventory.item_name).all()

    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(['Item Name', 'Quantity', 'Unit', 'Description', 'Center'])

    # Write data
    for item in inventory_data:
        writer.writerow([
            item.item_name,
            item.quantity,
            item.unit,
            item.description or 'N/A',
            item.center_name
        ])

    # Prepare response
    output.seek(0)
    filename = f'inventory_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

def generate_activities_report(start_date, end_date):
    # Query for activities data
    query = db.session.query(
        Activity.title,
        Activity.description,
        Activity.date,
        Activity.is_active,
        User.username.label('created_by')
    ).join(User, Activity.user_id == User.id)

    if start_date:
        query = query.filter(Activity.date >= start_date)

    if end_date:
        query = query.filter(Activity.date <= end_date)

    # Order by date
    activities_data = query.order_by(Activity.date.desc()).all()

    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(['Title', 'Description', 'Date', 'Active', 'Created By'])

    # Write data
    for activity in activities_data:
        writer.writerow([
            activity.title,
            activity.description,
            activity.date.strftime('%Y-%m-%d'),
            'Yes' if activity.is_active else 'No',
            activity.created_by
        ])

    # Prepare response
    output.seek(0)
    filename = f'activities_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

# Complaints Management
@admin_bp.route('/complaints')
@login_required
@admin_required
def complaints():
    complaints = Complaint.query.order_by(Complaint.created_at.desc()).all()
    return render_template('admin/complaints.html', complaints=complaints)

@admin_bp.route('/complaints/update-status/<int:id>', methods=['POST'])
@login_required
@admin_required
def update_complaint_status(id):
    complaint = Complaint.query.get_or_404(id)
    status = request.form.get('status')

    if status not in ['pending', 'in-progress', 'resolved']:
        flash('Invalid status value', 'danger')
        return redirect(url_for('admin.complaints'))

    complaint.status = status
    if status == 'resolved':
        complaint.resolved_at = datetime.utcnow()

    db.session.commit()
    flash('Complaint status updated successfully', 'success')
    return redirect(url_for('admin.complaints'))