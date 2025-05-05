from flask import Blueprint, render_template, request, flash, redirect, url_for
from models import NutritionTip, Activity, Center, Complaint
from forms import ComplaintForm
from app import db
from datetime import datetime

home_bp = Blueprint('home', __name__)

@home_bp.route('/')
def index():
    # Get latest nutrition tips and activities
    nutrition_tips = NutritionTip.query.filter_by(is_active=True).order_by(NutritionTip.created_at.desc()).limit(5).all()
    activities = Activity.query.filter_by(is_active=True).order_by(Activity.date.desc()).limit(5).all()
    complaint_form = ComplaintForm()
    
    return render_template('home/index.html', 
                          nutrition_tips=nutrition_tips, 
                          activities=activities,
                          complaint_form=complaint_form,
                          current_year=datetime.now().year)

@home_bp.route('/about')
def about():
    # Get all centers for About Us page
    centers = Center.query.all()
    return render_template('home/about.html', centers=centers, current_year=datetime.now().year)

@home_bp.route('/submit-complaint', methods=['POST'])
def submit_complaint():
    form = ComplaintForm()
    
    if form.validate_on_submit():
        new_complaint = Complaint(
            name=form.name.data,
            email=form.email.data,
            subject=form.subject.data,
            message=form.message.data,
            status='pending'
        )
        
        db.session.add(new_complaint)
        db.session.commit()
        
        flash('Your complaint has been submitted successfully!', 'success')
    else:
        flash('There was an error with your submission. Please check the form.', 'danger')
    
    return redirect(url_for('home.index'))
