from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from database import db, User, Loan, EMI
from models import LoanCalculator, LoanValidator, LOAN_CRITERIA
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///loan_management.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create tables
with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        annual_income = float(request.form['annual_income'])
        employment_status = request.form['employment_status']
        credit_score = int(request.form['credit_score'])
        date_of_birth = datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d')
        
        # Handle optional fields
        employment_start_date = None
        if request.form.get('employment_start_date'):
            employment_start_date = datetime.strptime(request.form['employment_start_date'], '%Y-%m-%d')
        
        existing_emis = float(request.form.get('existing_emis', 0))
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists!', 'error')
            return redirect(url_for('register'))
        
        # Validate credit score
        if credit_score < 300 or credit_score > 850:
            flash('Credit score must be between 300 and 850', 'error')
            return redirect(url_for('register'))
        
        # Create new user
        hashed_password = generate_password_hash(password)
        new_user = User(
            username=username, 
            email=email, 
            password=hashed_password,
            annual_income=annual_income,
            employment_status=employment_status,
            credit_score=credit_score,
            date_of_birth=date_of_birth,
            employment_start_date=employment_start_date,
            existing_emis=existing_emis
        )
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials!', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_loans = Loan.query.filter_by(user_id=current_user.id).all()
    total_loans = len(user_loans)
    approved_loans = len([loan for loan in user_loans if loan.status == 'Approved'])
    pending_loans = len([loan for loan in user_loans if loan.status == 'Pending'])
    rejected_loans = len([loan for loan in user_loans if loan.status == 'Rejected'])
    
    # Calculate total loan amount
    total_loan_amount = sum(loan.loan_amount for loan in user_loans if loan.status == 'Approved')
    
    return render_template('dashboard.html', 
                         total_loans=total_loans,
                         approved_loans=approved_loans,
                         pending_loans=pending_loans,
                         rejected_loans=rejected_loans,
                         total_loan_amount=total_loan_amount)

@app.route('/apply_loan', methods=['GET', 'POST'])
@login_required
def apply_loan():
    if request.method == 'POST':
        loan_amount = float(request.form['loan_amount'])
        interest_rate = float(request.form['interest_rate'])
        loan_term = int(request.form['loan_term'])
        loan_type = request.form['loan_type']
        
        # Validate loan application
        issues, calculations = LoanValidator.validate_loan_application(
            current_user, loan_amount, interest_rate, loan_term, loan_type
        )
        
        if issues:
            # Auto-reject with detailed reasons
            status = 'Rejected'
            rejection_reason = ' | '.join(issues)
            flash(f'Loan application automatically rejected: {rejection_reason}', 'error')
        else:
            # Passed all criteria - set to pending for manual review
            status = 'Pending'
            rejection_reason = None
            flash('Loan application submitted successfully! Under review.', 'success')
        
        new_loan = Loan(
            user_id=current_user.id,
            loan_amount=loan_amount,
            interest_rate=interest_rate,
            loan_term=loan_term,
            loan_type=loan_type,
            status=status,
            rejection_reason=rejection_reason
        )
        
        db.session.add(new_loan)
        db.session.commit()
        
        return redirect(url_for('view_loans'))
    
    return render_template('apply_loan.html')

@app.route('/view_loans')
@login_required
def view_loans():
    loans = Loan.query.filter_by(user_id=current_user.id).all()
    return render_template('view_loans.html', loans=loans)

@app.route('/emi_calculator', methods=['GET', 'POST'])
def emi_calculator():
    if request.method == 'POST':
        loan_amount = float(request.form['loan_amount'])
        interest_rate = float(request.form['interest_rate'])
        loan_term = int(request.form['loan_term'])
        
        emi = LoanCalculator.calculate_emi(loan_amount, interest_rate, loan_term)
        total_interest = LoanCalculator.calculate_total_interest(loan_amount, interest_rate, loan_term)
        total_payment = loan_amount + total_interest
        
        schedule = LoanCalculator.generate_emi_schedule(
            loan_amount, interest_rate, loan_term, datetime.now()
        )
        
        return render_template('emi_calculator.html', 
                             emi=emi, 
                             total_interest=total_interest,
                             total_payment=total_payment,
                             schedule=schedule[:12])  # Show first 12 months
    
    return render_template('emi_calculator.html')

@app.route('/payment_history/<int:loan_id>')
@login_required
def payment_history(loan_id):
    loan = Loan.query.get_or_404(loan_id)
    
    # Check if user owns this loan
    if loan.user_id != current_user.id:
        flash('Access denied!', 'error')
        return redirect(url_for('dashboard'))
    
    emis = EMI.query.filter_by(loan_id=loan_id).order_by(EMI.emi_number).all()
    
    # If no EMI records exist, generate them
    if not emis and loan.status == 'Approved':
        schedule = LoanCalculator.generate_emi_schedule(
            loan.loan_amount, loan.interest_rate, loan.loan_term, loan.start_date or datetime.now()
        )
        
        for emi_data in schedule:
            emi = EMI(
                loan_id=loan_id,
                emi_number=emi_data['emi_number'],
                due_date=emi_data['due_date'],
                amount_due=emi_data['emi_amount'],
                principal_amount=emi_data['principal_component'],
                interest_amount=emi_data['interest_component'],
                status='Pending'
            )
            db.session.add(emi)
        
        db.session.commit()
        emis = EMI.query.filter_by(loan_id=loan_id).order_by(EMI.emi_number).all()
    
    return render_template('payment_history.html', loan=loan, emis=emis)

@app.route('/api/calculate_emi', methods=['POST'])
def api_calculate_emi():
    data = request.get_json()
    loan_amount = float(data['loan_amount'])
    interest_rate = float(data['interest_rate'])
    loan_term = int(data['loan_term'])
    
    emi = LoanCalculator.calculate_emi(loan_amount, interest_rate, loan_term)
    total_interest = LoanCalculator.calculate_total_interest(loan_amount, interest_rate, loan_term)
    total_payment = loan_amount + total_interest
    
    return jsonify({
        'emi': emi,
        'total_interest': total_interest,
        'total_payment': total_payment
    })

if __name__ == '__main__':
    app.run(debug=True)