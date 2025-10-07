from datetime import datetime
from flask_login import UserMixin
from sqlalchemy import func
from .extensions import db
from passlib.hash import bcrypt


class User(db.Model, UserMixin):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(120), nullable=False)
	email = db.Column(db.String(120), unique=True, nullable=False)
	department = db.Column(db.String(80), nullable=True)
	roll_number = db.Column(db.String(50), unique=True, nullable=True)
	role = db.Column(db.String(20), default="student")  # student | teacher | admin
	password_hash = db.Column(db.String(255), nullable=False)
	created_at = db.Column(db.DateTime, server_default=func.now())

	profile = db.relationship("StudentProfile", backref="user", uselist=False)
	results = db.relationship("Result", backref="user", lazy=True)
	attendance_records = db.relationship("Attendance", backref="user", lazy=True)
	fee_payments = db.relationship("FeePayment", backref="user", lazy=True)
	leaves = db.relationship("LeaveApplication", backref="user", lazy=True)

	def set_password(self, password: str) -> None:
		self.password_hash = bcrypt.hash(password)

	def check_password(self, password: str) -> bool:
		return bcrypt.verify(password, self.password_hash)


class StudentProfile(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
	phone = db.Column(db.String(30))
	address = db.Column(db.String(255))
	bio = db.Column(db.Text)
	avatar_url = db.Column(db.String(255))
	
	# Additional profile fields
	date_of_birth = db.Column(db.Date)
	gender = db.Column(db.String(10))  # Male, Female, Other
	blood_group = db.Column(db.String(5))
	emergency_contact = db.Column(db.String(30))
	emergency_contact_name = db.Column(db.String(100))
	
	# Academic information
	year_of_study = db.Column(db.String(10))  # 1st Year, 2nd Year, etc.
	semester = db.Column(db.String(10))  # 1st Sem, 2nd Sem, etc.
	cgpa = db.Column(db.Float)
	
	# Professional information
	linkedin_url = db.Column(db.String(255))
	github_url = db.Column(db.String(255))
	portfolio_url = db.Column(db.String(255))
	resume_url = db.Column(db.String(255))
	
	# Skills and certifications
	skills = db.Column(db.Text)  # JSON string of skills
	certifications = db.Column(db.Text)  # JSON string of certifications
	interests = db.Column(db.Text)  # JSON string of interests
	
	# Social media
	twitter_url = db.Column(db.String(255))
	instagram_url = db.Column(db.String(255))
	
	# Additional notes
	notes = db.Column(db.Text)

	# (removed) Last known location


class Test(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	subject = db.Column(db.String(120), nullable=False)
	description = db.Column(db.String(255))
	created_by = db.Column(db.Integer, db.ForeignKey("user.id"))
	department = db.Column(db.String(80))
	total_marks = db.Column(db.Integer, default=0)
	time_limit_minutes = db.Column(db.Integer, default=0)
	is_published = db.Column(db.Boolean, default=False)
	created_at = db.Column(db.DateTime, server_default=func.now())
	ai_validated = db.Column(db.Boolean, default=False)
	ai_validation_notes = db.Column(db.Text)

	questions = db.relationship("Question", backref="test", cascade="all, delete-orphan")


class Question(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	test_id = db.Column(db.Integer, db.ForeignKey("test.id"), nullable=False)
	question = db.Column(db.Text, nullable=False)
	option1 = db.Column(db.String(255), nullable=False)
	option2 = db.Column(db.String(255), nullable=False)
	option3 = db.Column(db.String(255), nullable=False)
	option4 = db.Column(db.String(255), nullable=False)
	correct = db.Column(db.String(255), nullable=False)
	difficulty = db.Column(db.String(20))


class Result(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
	test_id = db.Column(db.Integer, db.ForeignKey("test.id"))
	subject = db.Column(db.String(120), nullable=False)
	marks = db.Column(db.Integer, nullable=False)
	total = db.Column(db.Integer, nullable=False)
	timestamp = db.Column(db.DateTime, default=datetime.utcnow)
	meta = db.Column(db.JSON, default=dict)


class Attendance(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
	date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
	status = db.Column(db.String(20), nullable=False, default="present")  # present | absent | leave
	remarks = db.Column(db.String(255))


class LeaveApplication(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
	reason = db.Column(db.Text, nullable=False)
	from_date = db.Column(db.Date, nullable=False)
	to_date = db.Column(db.Date, nullable=False)
	status = db.Column(db.String(20), default="pending")  # pending | approved | rejected
	ai_summary = db.Column(db.Text)
	created_at = db.Column(db.DateTime, server_default=func.now())


class FeePayment(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
	amount = db.Column(db.Numeric(10, 2), nullable=False)
	status = db.Column(db.String(20), default="success")  # success | failed | pending
	receipt_number = db.Column(db.String(64), unique=True)
	payment_type = db.Column(db.String(20), default="fees")  # fees | attendance_fine
	attendance_percentage = db.Column(db.Float)  # for attendance fine payments
	created_at = db.Column(db.DateTime, server_default=func.now())


class FeeStructure(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	department = db.Column(db.String(80), nullable=False)
	semester = db.Column(db.String(20), nullable=False)
	total_fees = db.Column(db.Numeric(10, 2), nullable=False)
	due_date = db.Column(db.Date)
	academic_year = db.Column(db.String(20), default="2024-25")
	created_at = db.Column(db.DateTime, server_default=func.now())


# ===== CODING PLATFORM MODELS =====

class CodingProblem(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	title = db.Column(db.String(200), nullable=False)
	description = db.Column(db.Text, nullable=False)
	difficulty = db.Column(db.String(20), nullable=False)  # easy | medium | hard
	category = db.Column(db.String(100), nullable=False)  # algorithms | data-structures | etc.
	time_limit = db.Column(db.Integer, default=5)  # seconds
	memory_limit = db.Column(db.Integer, default=128)  # MB
	created_by = db.Column(db.Integer, db.ForeignKey("user.id"))
	is_published = db.Column(db.Boolean, default=False)
	created_at = db.Column(db.DateTime, server_default=func.now())
	
	# AI-generated content
	ai_generated = db.Column(db.Boolean, default=False)
	ai_validation_notes = db.Column(db.Text)
	
	# Relationships
	test_cases = db.relationship("TestCase", backref="problem", cascade="all, delete-orphan")
	submissions = db.relationship("CodeSubmission", backref="problem", cascade="all, delete-orphan")


class TestCase(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	problem_id = db.Column(db.Integer, db.ForeignKey("coding_problem.id"), nullable=False)
	input_data = db.Column(db.Text, nullable=False)
	expected_output = db.Column(db.Text, nullable=False)
	is_hidden = db.Column(db.Boolean, default=False)  # Hidden test cases for final evaluation
	points = db.Column(db.Integer, default=10)


class CodeSubmission(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
	problem_id = db.Column(db.Integer, db.ForeignKey("coding_problem.id"), nullable=False)
	language = db.Column(db.String(20), nullable=False)  # python | java | cpp | c | javascript
	code = db.Column(db.Text, nullable=False)
	status = db.Column(db.String(20), default="pending")  # pending | accepted | wrong_answer | time_limit | runtime_error | compilation_error
	execution_time = db.Column(db.Float)  # seconds
	memory_used = db.Column(db.Float)  # MB
	score = db.Column(db.Integer, default=0)  # points earned
	total_test_cases = db.Column(db.Integer, default=0)
	passed_test_cases = db.Column(db.Integer, default=0)
	error_message = db.Column(db.Text)
	submitted_at = db.Column(db.DateTime, server_default=func.now())
	
	# Detailed results for each test case
	test_results = db.Column(db.JSON, default=list)


# ===== FACE LOCK =====
class FaceCredential(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
	embedding = db.Column(db.JSON, nullable=False)  # 128/512-d vector
	created_at = db.Column(db.DateTime, server_default=func.now())
