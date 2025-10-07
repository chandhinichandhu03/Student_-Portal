from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from ..extensions import db
from ..models import Test, Question, LeaveApplication, FeeStructure
from ..services.gemini_client import GeminiClient


admin_bp = Blueprint("admin", __name__)


def require_admin():
	return current_user.is_authenticated and current_user.role in ("admin", "teacher")


@admin_bp.route("/admin/tests")
@login_required
def admin_tests():
	if not require_admin():
		flash("Unauthorized", "danger")
		return redirect(url_for("main.dashboard"))
	items = Test.query.order_by(Test.created_at.desc()).all()
	return render_template("admin_tests.html", items=items)


@admin_bp.route("/admin/test/<int:test_id>/publish", methods=["POST"]) 
@login_required
def publish_test(test_id: int):
	if not require_admin():
		flash("Unauthorized", "danger")
		return redirect(url_for("main.dashboard"))
	test = db.session.get(Test, test_id)
	if not test:
		flash("Not found", "danger")
		return redirect(url_for("admin.admin_tests"))
	# AI validation
	client = GeminiClient()
	notes = []
	if client.enabled:
		try:
			payload = {
				"subject": test.subject,
				"questions": [
					{"q": q.question, "options": [q.option1, q.option2, q.option3, q.option4], "correct": q.correct}
					for q in test.questions
				]
			}
			import json
			prompt = (
				"Review this MCQ test for clarity, correctness, and ambiguity. "
				"Return JSON {valid: boolean, notes: string}. Test: " + json.dumps(payload)
			)
			resp = client.model.generate_content(prompt)
			data = json.loads(resp.text or "{}")
			valid = bool(data.get("valid", True))
			notes.append(data.get("notes") or "")
			test.ai_validated = valid
		except Exception:
			test.ai_validated = True
			notes.append("AI validation unavailable; defaulting to approved")
	else:
		test.ai_validated = True
		notes.append("No AI key; default approved")
	test.ai_validation_notes = "\n".join([n for n in notes if n])
	test.is_published = True
	db.session.commit()
	flash("Test published", "success")
	return redirect(url_for("admin.admin_tests"))


@admin_bp.route("/admin/question/<int:qid>", methods=["GET", "POST"]) 
@login_required
def edit_question(qid: int):
	if not require_admin():
		flash("Unauthorized", "danger")
		return redirect(url_for("main.dashboard"))
	q = db.session.get(Question, qid)
	if not q:
		flash("Not found", "danger")
		return redirect(url_for("admin.admin_tests"))
	if request.method == "POST":
		q.question = request.form.get("question")
		q.option1 = request.form.get("option1")
		q.option2 = request.form.get("option2")
		q.option3 = request.form.get("option3")
		q.option4 = request.form.get("option4")
		q.correct = request.form.get("correct")
		db.session.commit()
		flash("Question updated", "success")
		return redirect(url_for("admin.admin_tests"))
	return render_template("edit_question.html", q=q)


@admin_bp.route("/admin/fee_structure", methods=["GET", "POST"])
@login_required
def fee_structure():
	if not require_admin():
		flash("Unauthorized", "danger")
		return redirect(url_for("main.dashboard"))
	if request.method == "POST":
		department = request.form.get("department")
		semester = request.form.get("semester")
		total_fees = request.form.get("total_fees", type=float)
		due_date = request.form.get("due_date")
		academic_year = request.form.get("academic_year", "2024-25")

		# Parse due_date (string -> date)
		parsed_due_date = None
		if due_date:
			try:
				from datetime import datetime
				parsed_due_date = datetime.strptime(due_date, "%Y-%m-%d").date()
			except ValueError:
				parsed_due_date = None
		
		# Check if structure already exists
		existing = FeeStructure.query.filter_by(department=department, semester=semester, academic_year=academic_year).first()
		if existing:
			existing.total_fees = total_fees
			existing.due_date = parsed_due_date
		else:
			structure = FeeStructure(
				department=department,
				semester=semester,
				total_fees=total_fees,
				due_date=parsed_due_date,
				academic_year=academic_year
			)
			db.session.add(structure)
		db.session.commit()
		flash("Fee structure updated", "success")
		return redirect(url_for("admin.fee_structure"))
	
	structures = FeeStructure.query.order_by(FeeStructure.department, FeeStructure.semester).all()
	return render_template("fee_structure.html", structures=structures)


@admin_bp.route("/admin/leaves")
@login_required
def admin_leaves():
	if not require_admin():
		flash("Unauthorized", "danger")
		return redirect(url_for("main.dashboard"))
	leaves = LeaveApplication.query.order_by(LeaveApplication.created_at.desc()).all()
	return render_template("admin_leaves.html", leaves=leaves)


# Removed admin approve/reject endpoint to make leaves read-only


@admin_bp.route("/admin/test/<int:test_id>/delete", methods=["POST"])
@login_required
def delete_test(test_id: int):
	if not require_admin():
		flash("Unauthorized", "danger")
		return redirect(url_for("main.dashboard"))
	
	test = db.session.get(Test, test_id)
	if not test:
		flash("Test not found", "danger")
		return redirect(url_for("admin.admin_tests"))
	
	# Delete all questions first
	Question.query.filter_by(test_id=test_id).delete()
	
	# Delete the test
	db.session.delete(test)
	db.session.commit()
	
	flash("Test deleted successfully", "success")
	return redirect(url_for("admin.admin_tests"))


@admin_bp.route("/admin/test/<int:test_id>/regenerate", methods=["POST"])
@login_required
def regenerate_test(test_id: int):
	if not require_admin():
		flash("Unauthorized", "danger")
		return redirect(url_for("main.dashboard"))
	
	test = db.session.get(Test, test_id)
	if not test:
		flash("Test not found", "danger")
		return redirect(url_for("admin.admin_tests"))
	
	# Get new topic from form
	new_topic = request.form.get("new_topic", test.subject).strip()
	if not new_topic:
		flash("Please enter a valid topic", "danger")
		return redirect(url_for("admin.admin_tests"))
	
	try:
		# Delete existing questions first and commit
		existing_questions = Question.query.filter_by(test_id=test_id).all()
		for q in existing_questions:
			db.session.delete(q)
		db.session.commit()
		
		# Regenerate questions with new topic
		client = GeminiClient()
		if not client.enabled:
			flash("AI service not available", "danger")
			return redirect(url_for("admin.admin_tests"))
		
		# Generate new questions
		num_questions = test.total_marks or 5
		questions_data = client.generate_mcqs(
			topic=new_topic,
			num_questions=num_questions
		)
		
		if not questions_data:
			flash("Failed to generate questions", "danger")
			return redirect(url_for("admin.admin_tests"))
		
		# Add new questions
		for q_data in questions_data:
			question = Question(
				test_id=test_id,
				question=q_data["question"],
				option1=q_data["options"][0],
				option2=q_data["options"][1],
				option3=q_data["options"][2],
				option4=q_data["options"][3],
				correct=q_data["correct"]
			)
			db.session.add(question)
		
		# Update test subject and metadata
		test.subject = new_topic
		test.ai_validated = False
		test.ai_validation_notes = f"Regenerated with new topic: {new_topic}"
		test.total_marks = len(questions_data)
		
		db.session.commit()
		flash(f"Test regenerated successfully with {len(questions_data)} questions on '{new_topic}'", "success")
		
	except Exception as e:
		db.session.rollback()
		flash(f"Error regenerating test: {str(e)}", "danger")
	
	return redirect(url_for("admin.admin_tests"))
