from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from ..extensions import db
from ..models import User, StudentProfile, Result, Attendance, FeePayment, LeaveApplication, Test, FeeStructure
from datetime import datetime
from ..services.gemini_client import GeminiClient


main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
	return render_template("index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
	if current_user.role in ("admin", "teacher"):
		students_count = User.query.filter_by(role="student").count()
		tests_count = Test.query.count()
		results_recent = Result.query.order_by(Result.timestamp.desc()).limit(10).all()
		return render_template("dashboard_admin.html", students_count=students_count, tests_count=tests_count, results_recent=results_recent)
	else:
		upcoming_tests = Test.query.filter((Test.is_published == True) & ((Test.department == None) | (Test.department == current_user.department))).order_by(Test.created_at.desc()).limit(5).all()
		past_results = Result.query.filter_by(student_id=current_user.id).order_by(Result.timestamp.desc()).limit(5).all()
		return render_template("dashboard_student.html", upcoming_tests=upcoming_tests, past_results=past_results)


@main_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
	profile = current_user.profile
	if request.method == "POST":
		# Photo upload handling
		if 'avatar' in request.files and request.files['avatar'] and request.files['avatar'].filename:
			file = request.files['avatar']
			import os
			from werkzeug.utils import secure_filename
			filename = secure_filename(file.filename)
			upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'avatars')
			os.makedirs(upload_dir, exist_ok=True)
			file_path = os.path.join(upload_dir, f"user_{current_user.id}_{filename}")
			file.save(file_path)
			# Save relative URL
			rel_path = file_path.split(current_app.root_path)[-1].lstrip('/')
			profile.avatar_url = '/' + rel_path.replace('\\', '/')
			
		# Basic user information
		current_user.name = request.form.get("name")
		current_user.department = request.form.get("department")
		
		# Contact information
		profile.phone = request.form.get("phone")
		profile.address = request.form.get("address")
		profile.bio = request.form.get("bio")
		
		# Personal information
		dob_str = request.form.get("date_of_birth")
		if dob_str:
			try:
				from datetime import datetime
				profile.date_of_birth = datetime.strptime(dob_str, "%Y-%m-%d").date()
			except ValueError:
				pass
		profile.gender = request.form.get("gender")
		profile.blood_group = request.form.get("blood_group")
		profile.emergency_contact = request.form.get("emergency_contact")
		profile.emergency_contact_name = request.form.get("emergency_contact_name")
		
		# Academic information
		profile.year_of_study = request.form.get("year_of_study")
		profile.semester = request.form.get("semester")
		cgpa_str = request.form.get("cgpa")
		if cgpa_str:
			try:
				profile.cgpa = float(cgpa_str)
			except ValueError:
				pass
		
		# Professional information
		profile.linkedin_url = request.form.get("linkedin_url")
		profile.github_url = request.form.get("github_url")
		profile.portfolio_url = request.form.get("portfolio_url")
		profile.resume_url = request.form.get("resume_url")
		
		# Skills and certifications (stored as JSON strings)
		import json
		skills_list = [skill.strip() for skill in request.form.get("skills", "").split(",") if skill.strip()]
		profile.skills = json.dumps(skills_list) if skills_list else None
		
		certifications_list = [cert.strip() for cert in request.form.get("certifications", "").split(",") if cert.strip()]
		profile.certifications = json.dumps(certifications_list) if certifications_list else None
		
		interests_list = [interest.strip() for interest in request.form.get("interests", "").split(",") if interest.strip()]
		profile.interests = json.dumps(interests_list) if interests_list else None
		
		# Social media
		profile.twitter_url = request.form.get("twitter_url")
		profile.instagram_url = request.form.get("instagram_url")
		
		# Additional notes
		profile.notes = request.form.get("notes")
		
		db.session.commit()
		flash("Profile updated successfully!", "success")
		return redirect(url_for("main.profile"))
	return render_template("profile.html", profile=profile)


@main_bp.route("/fees", methods=["GET", "POST"])
@login_required
def fees():
	if request.method == "POST":
		amount = request.form.get("amount", type=float)
		payment_type = request.form.get("payment_type", "fees")
		if not amount or amount <= 0:
			flash("Invalid amount", "danger")
			return redirect(url_for("main.fees"))
		
		# Calculate attendance percentage for fine payments
		attendance_pct = None
		if payment_type == "attendance_fine":
			recs = Attendance.query.filter_by(student_id=current_user.id).all()
			total_days = len(recs)
			present_days = len([r for r in recs if r.status == "present"]) if total_days else 0
			attendance_pct = (present_days * 100.0 / total_days) if total_days else 100.0
			# If attendance is below 75%, flip oldest absences to present until reaching 75%
			if total_days and attendance_pct < 75:
				import math
				needed_present = math.ceil(0.75 * total_days - present_days)
				if needed_present > 0:
					absents = Attendance.query.filter_by(student_id=current_user.id, status="absent").order_by(Attendance.date.asc()).limit(needed_present).all()
					for rec in absents:
						rec.status = "present"
						rec.remarks = (rec.remarks or "").strip()
						rec.remarks = (rec.remarks + " ").strip() + "(fine adjusted)"
					# Recompute after adjustment
					recs = Attendance.query.filter_by(student_id=current_user.id).all()
					total_days = len(recs)
					present_days = len([r for r in recs if r.status == "present"]) if total_days else 0
					attendance_pct = (present_days * 100.0 / total_days) if total_days else 100.0
		
		from datetime import datetime
		import random
		receipt_number = f"RCPT{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{current_user.id}{random.randint(100,999)}"
		payment = FeePayment(
			student_id=current_user.id, 
			amount=amount, 
			status="success", 
			receipt_number=receipt_number,
			payment_type=payment_type,
			attendance_percentage=attendance_pct
		)
		db.session.add(payment)
		db.session.commit()
		flash("Payment successful", "success")
		return redirect(url_for("main.fees"))
	
	# Calculate attendance percentage and fine amount
	recs = Attendance.query.filter_by(student_id=current_user.id).all()
	total_days = len(recs)
	present_days = len([r for r in recs if r.status == "present"]) if total_days else 0
	attendance_pct = (present_days * 100.0 / total_days) if total_days else 100.0
	
	# Calculate fine if attendance < 75%
	fine_amount = 0
	if attendance_pct < 75:
		shortage = 75 - attendance_pct
		fine_amount = shortage * 1000  # 1000 per percentage point
	
	# Get fee structure for student's department
	fee_structure = FeeStructure.query.filter_by(department=current_user.department).first()
	total_fees_due = fee_structure.total_fees if fee_structure else 50000  # default
	
	# Calculate paid amount (only successful regular fees payments)
	paid_fees = db.session.query(db.func.sum(FeePayment.amount)).filter(
		FeePayment.student_id == current_user.id,
		FeePayment.payment_type == "fees",
		FeePayment.status == "success"
	).scalar() or 0
	
	pending_amount = float(total_fees_due) - float(paid_fees)
	
	payments = FeePayment.query.filter_by(student_id=current_user.id).order_by(FeePayment.created_at.desc()).all()
	return render_template("fees.html", 
		payments=payments, 
		attendance_pct=attendance_pct, 
		fine_amount=fine_amount,
		total_fees_due=total_fees_due,
		paid_fees=paid_fees,
		pending_amount=pending_amount,
		fee_structure=fee_structure
	)


@main_bp.route("/attendance", methods=["GET", "POST"])
@login_required
def attendance():
	if request.method == "POST":
		status = request.form.get("status", "present")
		remarks = request.form.get("remarks")
		# upsert for today
		rec = Attendance.query.filter_by(student_id=current_user.id, date=date.today()).first()
		if not rec:
			rec = Attendance(student_id=current_user.id, date=date.today(), status=status, remarks=remarks)
			db.session.add(rec)
		else:
			rec.status = status
			rec.remarks = remarks
		db.session.commit()
		flash("Attendance marked", "success")
		records = Attendance.query.filter_by(student_id=current_user.id).order_by(Attendance.date.desc()).all()
		return render_template("attendance.html", records=records)
	records = Attendance.query.filter_by(student_id=current_user.id).order_by(Attendance.date.desc()).all()
	return render_template("attendance.html", records=records)


@main_bp.route("/leave", methods=["GET", "POST"])
@login_required
def leave():
	if request.method == "POST":
		reason = request.form.get("reason")
		from_date_str = request.form.get("from_date")
		to_date_str = request.form.get("to_date")
		try:
			from_date = datetime.strptime(from_date_str, "%Y-%m-%d").date() if from_date_str else None
			to_date = datetime.strptime(to_date_str, "%Y-%m-%d").date() if to_date_str else None
		except ValueError:
			flash("Invalid date format", "danger")
			return redirect(url_for("main.leave"))
		# Decide solely based on reason using AI (or heuristic fallback)
		client = GeminiClient()
		status = "pending"
		rationale_parts = []
		reason_l = (reason or "").lower()
		strong_medical = [
			"cancer", "chemotherapy", "chemo", "surgery", "operation", "hospitalized",
			"emergency", "accident", "injury", "doctor appointment", "medical certificate",
			"serious illness", "critical", "funeral", "bereavement", "death", "covid",
		]
		soft_keywords = [
			"medical", "hospital", "health", "exam", "ceremony", "function", "family",
			"urgent", "emergency", "appointment", "sick", "fever", "illness",
		]
		# Immediate approval for strong medical emergencies
		if any(k in reason_l for k in strong_medical):
			status = "approved"
			rationale_parts.append("Recognized strong medical emergency → approved")
		else:
			if client.enabled:
				prompt = (
					"Act as a fair and empathetic college teacher deciding on a student's leave request. "
					f"Reason: '{reason}'. Dates: {from_date} to {to_date}. "
					"Consider legitimacy, urgency, and academic impact. Prioritize health and family emergencies. "
					"Reply ONLY in strict JSON: {decision: 'approve'|'reject', justification: string}."
				)
				try:
					resp = client.model.generate_content(prompt)
					import json
					data = json.loads(resp.text or "{}")
					decision = (data.get("decision") or "reject").lower()
					just = data.get("justification") or ""
					status = "approved" if decision == "approve" else "rejected"
					rationale_parts.append(f"AI: {decision}. {just}")
				except Exception:
					status = "approved" if any(k in reason_l for k in (soft_keywords + strong_medical)) else "rejected"
					rationale_parts.append("Heuristic decision due to AI error")
			else:
				status = "approved" if any(k in reason_l for k in (soft_keywords + strong_medical)) else "rejected"
				rationale_parts.append("Heuristic decision (no AI key)")

		ai_summary = f"Auto-evaluated based on reason only. {' '.join(rationale_parts)}"
		app = LeaveApplication(student_id=current_user.id, reason=reason, from_date=from_date, to_date=to_date, ai_summary=ai_summary, status=status)
		db.session.add(app)
		db.session.commit()
		flash(f"Leave request {status}", "success" if status == "approved" else "warning")
		return redirect(url_for("main.leave"))
	apps = LeaveApplication.query.filter_by(student_id=current_user.id).order_by(LeaveApplication.created_at.desc()).all()
	return render_template("leave.html", apps=apps)


@main_bp.route("/leaderboard")
@login_required
def leaderboard():
	# top by average percentage
	from sqlalchemy import func
	q = db.session.query(Result.student_id, func.avg((Result.marks * 100.0) / Result.total).label("avg_pct"))\
		.group_by(Result.student_id)\
		.order_by(func.avg((Result.marks * 100.0) / Result.total).desc())\
		.limit(20).all()
	items = []
	for sid, avg_pct in q:
		user = db.session.get(User, sid)
		items.append({"user": user, "avg_pct": round(avg_pct, 2)})
	return render_template("leaderboard.html", items=items)


@main_bp.route("/results")
@login_required
def results():
	items = Result.query.filter_by(student_id=current_user.id).order_by(Result.timestamp.desc()).all()
	return render_template("results.html", items=items)


@main_bp.route("/download_receipt/<int:payment_id>")
@login_required
def download_receipt(payment_id: int):
	payment = FeePayment.query.filter_by(id=payment_id, student_id=current_user.id).first()
	if not payment:
		flash("Receipt not found", "danger")
		return redirect(url_for("main.fees"))
	
	# Generate receipt content
	receipt_content = f"""
STUDENT PORTAL - PAYMENT RECEIPT
================================

Receipt Number: {payment.receipt_number}
Student: {current_user.name}
Email: {current_user.email}
Department: {current_user.department}
Payment Type: {payment.payment_type.replace('_', ' ').title()}
Amount: ₹{payment.amount}
Status: {payment.status.upper()}
Date: {payment.created_at.strftime('%Y-%m-%d %H:%M:%S')}

"""
	
	if payment.payment_type == "attendance_fine" and payment.attendance_percentage:
		receipt_content += f"Attendance Percentage: {payment.attendance_percentage:.1f}%\n"
	
	receipt_content += """
Thank you for your payment!

This is a computer-generated receipt.
================================
"""
	
	from flask import Response
	return Response(
		receipt_content,
		mimetype='text/plain',
		headers={
			'Content-Disposition': f'attachment; filename=receipt_{payment.receipt_number}.txt'
		}
	)
