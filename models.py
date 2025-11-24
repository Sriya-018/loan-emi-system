from datetime import datetime, timedelta
import math

# Loan type specific criteria
LOAN_CRITERIA = {
    'Personal Loan': {
        'min_age': 21,
        'max_age_maturity': 65,
        'min_income': 300000,
        'min_employment_years': 1,
        'min_credit_score': 650,
        'max_dti_ratio': 40,
        'min_interest_rate': 10.5,
        'max_loan_to_income': 5
    },
    'Home Loan': {
        'min_age': 21,
        'max_age_maturity': 70,
        'min_income': 600000,
        'min_employment_years': 2,
        'min_credit_score': 700,
        'max_dti_ratio': 35,
        'min_interest_rate': 8.5,
        'max_loan_to_income': 6
    },
    'Car Loan': {
        'min_age': 21,
        'max_age_maturity': 65,
        'min_income': 400000,
        'min_employment_years': 1,
        'min_credit_score': 600,
        'max_dti_ratio': 45,
        'min_interest_rate': 7.5,
        'max_loan_to_income': 5
    },
    'Education Loan': {
        'min_age': 18,
        'max_age_maturity': 35,
        'min_income': 0,
        'min_employment_years': 0,
        'min_credit_score': 550,
        'max_dti_ratio': 0,
        'min_interest_rate': 8.0,
        'max_loan_to_income': 10  # Higher for education
    },
    'Business Loan': {
        'min_age': 25,
        'max_age_maturity': 65,
        'min_income': 800000,
        'min_employment_years': 3,
        'min_credit_score': 720,
        'max_dti_ratio': 30,
        'min_interest_rate': 11.0,
        'max_loan_to_income': 4
    }
}

class LoanCalculator:
    @staticmethod
    def calculate_emi(principal, annual_rate, tenure_months):
        """Calculate EMI using the formula: EMI = P * r * (1+r)^n / ((1+r)^n - 1)"""
        monthly_rate = annual_rate / 12 / 100
        emi = (principal * monthly_rate * math.pow(1 + monthly_rate, tenure_months)) / (
            math.pow(1 + monthly_rate, tenure_months) - 1
        )
        return round(emi, 2)
    
    @staticmethod
    def generate_emi_schedule(loan_amount, interest_rate, loan_term, start_date):
        """Generate complete EMI schedule for a loan"""
        emi_amount = LoanCalculator.calculate_emi(loan_amount, interest_rate, loan_term)
        monthly_rate = interest_rate / 12 / 100
        schedule = []
        
        remaining_principal = loan_amount
        
        for i in range(1, loan_term + 1):
            interest_component = remaining_principal * monthly_rate
            principal_component = emi_amount - interest_component
            
            # For the last EMI, adjust principal component
            if i == loan_term:
                principal_component = remaining_principal
                emi_amount = principal_component + interest_component
            
            due_date = start_date + timedelta(days=30 * i)
            
            schedule.append({
                'emi_number': i,
                'due_date': due_date,
                'emi_amount': round(emi_amount, 2),
                'principal_component': round(principal_component, 2),
                'interest_component': round(interest_component, 2),
                'remaining_principal': round(remaining_principal - principal_component, 2)
            })
            
            remaining_principal -= principal_component
        
        return schedule
    
    @staticmethod
    def calculate_total_interest(loan_amount, interest_rate, loan_term):
        """Calculate total interest payable"""
        emi = LoanCalculator.calculate_emi(loan_amount, interest_rate, loan_term)
        total_payment = emi * loan_term
        return round(total_payment - loan_amount, 2)

class LoanValidator:
    @staticmethod
    def calculate_age(birth_date):
        """Calculate age from birth date"""
        if not birth_date:
            return 0
        today = datetime.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    
    @staticmethod
    def calculate_employment_years(employment_start_date):
        """Calculate years of employment"""
        if not employment_start_date:
            return 0
        employment_duration = (datetime.today() - employment_start_date).days / 365.25
        return round(employment_duration, 1)
    
    @staticmethod
    def calculate_dti_ratio(user, new_loan_emi):
        """Calculate Debt-to-Income Ratio"""
        monthly_income = user.annual_income / 12
        total_monthly_debt = user.existing_emis + new_loan_emi
        if monthly_income == 0:
            return 100  # Maximum DTI if no income
        return (total_monthly_debt / monthly_income) * 100
    
    @staticmethod
    def validate_loan_application(user, loan_amount, interest_rate, loan_term, loan_type):
        """Validate loan application against criteria"""
        criteria = LOAN_CRITERIA.get(loan_type, LOAN_CRITERIA['Personal Loan'])
        issues = []
        
        # Calculate values
        age = LoanValidator.calculate_age(user.date_of_birth)
        employment_years = LoanValidator.calculate_employment_years(user.employment_start_date)
        new_loan_emi = LoanCalculator.calculate_emi(loan_amount, interest_rate, loan_term)
        dti_ratio = LoanValidator.calculate_dti_ratio(user, new_loan_emi)
        loan_to_income = loan_amount / user.annual_income if user.annual_income > 0 else float('inf')
        age_at_maturity = age + (loan_term / 12)
        
        # Age validation
        if age < criteria['min_age']:
            issues.append(f"Minimum age required: {criteria['min_age']} years")
        if age_at_maturity > criteria['max_age_maturity']:
            issues.append(f"Maximum age at loan maturity: {criteria['max_age_maturity']} years")
        
        # Income validation
        if user.annual_income < criteria['min_income']:
            issues.append(f"Minimum annual income required: ₹{criteria['min_income']:,.0f}")
        
        # Employment validation
        if employment_years < criteria['min_employment_years']:
            issues.append(f"Minimum employment years required: {criteria['min_employment_years']}")
        
        # Credit score validation
        if user.credit_score < criteria['min_credit_score']:
            issues.append(f"Minimum credit score required: {criteria['min_credit_score']}")
        
        # DTI ratio validation
        if dti_ratio > criteria['max_dti_ratio']:
            issues.append(f"Maximum Debt-to-Income ratio: {criteria['max_dti_ratio']}% (Your DTI: {dti_ratio:.1f}%)")
        
        # Interest rate validation
        if interest_rate < criteria['min_interest_rate']:
            issues.append(f"Minimum interest rate: {criteria['min_interest_rate']}%")
        
        # Loan to income ratio
        if loan_to_income > criteria['max_loan_to_income']:
            issues.append(f"Maximum loan-to-income ratio: {criteria['max_loan_to_income']}x")
        
        return issues, {
            'age': age,
            'employment_years': employment_years,
            'dti_ratio': dti_ratio,
            'loan_to_income': loan_to_income,
            'age_at_maturity': age_at_maturity
        }