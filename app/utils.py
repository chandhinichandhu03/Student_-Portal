from .extensions import db
from .models import User
from flask import current_app


def ensure_default_admin() -> None:
	email = current_app.config.get("DEFAULT_ADMIN_EMAIL")
	password = current_app.config.get("DEFAULT_ADMIN_PASSWORD")
	if not email or not password:
		return
	existing = User.query.filter_by(email=email).first()
	if existing:
		return
	admin = User(name="Admin", email=email, department="Administration", role="admin", roll_number=None, password_hash="")
	admin.set_password(password)
	db.session.add(admin)
	db.session.commit()


def migrate_schema() -> None:
	# Add columns to Test table if missing (SQLite-safe)
	engine = db.get_engine()
	with engine.connect() as conn:
		# Detect existing columns
		res = conn.exec_driver_sql("PRAGMA table_info(test)")
		cols = {row[1] for row in res.fetchall()}
		if "ai_validated" not in cols:
			try:
				conn.exec_driver_sql("ALTER TABLE test ADD COLUMN ai_validated BOOLEAN DEFAULT 0")
			except Exception:
				pass
		if "ai_validation_notes" not in cols:
			try:
				conn.exec_driver_sql("ALTER TABLE test ADD COLUMN ai_validation_notes TEXT")
			except Exception:
				pass
		
		# Add columns to FeePayment table if missing
		res = conn.exec_driver_sql("PRAGMA table_info(fee_payment)")
		cols = {row[1] for row in res.fetchall()}
		if "payment_type" not in cols:
			try:
				conn.exec_driver_sql("ALTER TABLE fee_payment ADD COLUMN payment_type VARCHAR(20) DEFAULT 'fees'")
			except Exception:
				pass
		if "attendance_percentage" not in cols:
			try:
				conn.exec_driver_sql("ALTER TABLE fee_payment ADD COLUMN attendance_percentage FLOAT")
			except Exception:
				pass
		
		# Add columns to StudentProfile table if missing
		res = conn.exec_driver_sql("PRAGMA table_info(student_profile)")
		cols = {row[1] for row in res.fetchall()}
		new_profile_columns = [
			("date_of_birth", "DATE"),
			("gender", "VARCHAR(10)"),
			("blood_group", "VARCHAR(5)"),
			("emergency_contact", "VARCHAR(30)"),
			("emergency_contact_name", "VARCHAR(100)"),
			("year_of_study", "VARCHAR(10)"),
			("semester", "VARCHAR(10)"),
			("cgpa", "FLOAT"),
			("linkedin_url", "VARCHAR(255)"),
			("github_url", "VARCHAR(255)"),
			("portfolio_url", "VARCHAR(255)"),
			("resume_url", "VARCHAR(255)"),
			("skills", "TEXT"),
			("certifications", "TEXT"),
			("interests", "TEXT"),
			("twitter_url", "VARCHAR(255)"),
			("instagram_url", "VARCHAR(255)"),
			("notes", "TEXT")
		]
		for col_name, col_type in new_profile_columns:
			if col_name not in cols:
				try:
					conn.exec_driver_sql(f"ALTER TABLE student_profile ADD COLUMN {col_name} {col_type}")
				except Exception:
					pass

		# (removed) location tracking columns
		
		# Create fee_structure table if not exists
		try:
			conn.exec_driver_sql("""
				CREATE TABLE IF NOT EXISTS fee_structure (
					id INTEGER PRIMARY KEY,
					department VARCHAR(80) NOT NULL,
					semester VARCHAR(20) NOT NULL,
					total_fees DECIMAL(10,2) NOT NULL,
					due_date DATE,
					academic_year VARCHAR(20) DEFAULT '2024-25',
					created_at DATETIME DEFAULT CURRENT_TIMESTAMP
				)
			""")
		except Exception:
			pass
		
		# Create coding platform tables if not exists
		try:
			conn.exec_driver_sql("""
				CREATE TABLE IF NOT EXISTS coding_problem (
					id INTEGER PRIMARY KEY,
					title VARCHAR(200) NOT NULL,
					description TEXT NOT NULL,
					difficulty VARCHAR(20) NOT NULL,
					category VARCHAR(100) NOT NULL,
					time_limit INTEGER DEFAULT 5,
					memory_limit INTEGER DEFAULT 128,
					created_by INTEGER,
					is_published BOOLEAN DEFAULT 0,
					created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
					ai_generated BOOLEAN DEFAULT 0,
					ai_validation_notes TEXT,
					FOREIGN KEY (created_by) REFERENCES user (id)
				)
			""")
		except Exception:
			pass
		
		try:
			conn.exec_driver_sql("""
				CREATE TABLE IF NOT EXISTS test_case (
					id INTEGER PRIMARY KEY,
					problem_id INTEGER NOT NULL,
					input_data TEXT NOT NULL,
					expected_output TEXT NOT NULL,
					is_hidden BOOLEAN DEFAULT 0,
					points INTEGER DEFAULT 10,
					FOREIGN KEY (problem_id) REFERENCES coding_problem (id)
				)
			""")
		except Exception:
			pass
		
		try:
			conn.exec_driver_sql("""
				CREATE TABLE IF NOT EXISTS code_submission (
					id INTEGER PRIMARY KEY,
					student_id INTEGER NOT NULL,
					problem_id INTEGER NOT NULL,
					language VARCHAR(20) NOT NULL,
					code TEXT NOT NULL,
					status VARCHAR(20) DEFAULT 'pending',
					execution_time FLOAT,
					memory_used FLOAT,
					score INTEGER DEFAULT 0,
					total_test_cases INTEGER DEFAULT 0,
					passed_test_cases INTEGER DEFAULT 0,
					error_message TEXT,
					submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
					test_results JSON,
					FOREIGN KEY (student_id) REFERENCES user (id),
					FOREIGN KEY (problem_id) REFERENCES coding_problem (id)
				)
			""")
		except Exception:
			pass
