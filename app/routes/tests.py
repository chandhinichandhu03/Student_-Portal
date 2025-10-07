from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from ..extensions import db
from ..models import Test, Question, Result
from ..services.gemini_client import GeminiClient
import csv
from io import TextIOWrapper


tests_bp = Blueprint("tests", __name__)


@tests_bp.route("/generate_test", methods=["GET", "POST"])
@login_required
def generate_test():
	if current_user.role not in ("admin", "teacher"):
		flash("Unauthorized", "danger")
		return redirect(url_for("main.dashboard"))
	if request.method == "POST":
		topic = request.form.get("topic")
		num = request.form.get("num_questions", type=int) or 5
		time_limit = request.form.get("time_limit", type=int) or 0
		department = request.form.get("department")
		client = GeminiClient()
		mcqs = client.generate_mcqs(topic, num)
		test = Test(subject=topic, description=f"AI generated on {topic}", created_by=current_user.id, department=department, time_limit_minutes=time_limit, is_published=True, ai_validated=True)
		db.session.add(test)
		db.session.flush()
		for item in mcqs:
			q = Question(
				test_id=test.id,
				question=item["question"],
				option1=item["options"][0],
				option2=item["options"][1],
				option3=item["options"][2],
				option4=item["options"][3],
				correct=item["correct"],
				difficulty=item.get("difficulty"),
			)
			db.session.add(q)
		db.session.commit()
		flash("Test generated and published immediately.", "success")
		return redirect(url_for("tests.manage_tests"))
	return render_template("generate_test.html")


@tests_bp.route("/admin/create_test", methods=["GET", "POST"]) 
@login_required
def admin_create_test():
	if current_user.role not in ("admin", "teacher"):
		flash("Unauthorized", "danger")
		return redirect(url_for("main.dashboard"))
	return generate_test()


@tests_bp.route("/tests")
@login_required
def manage_tests():
	if current_user.role in ("admin", "teacher"):
		items = Test.query.order_by(Test.created_at.desc()).all()
	else:
		items = Test.query.filter_by(is_published=True).order_by(Test.created_at.desc()).all()
	return render_template("tests.html", items=items)


@tests_bp.route("/take_test/<int:test_id>", methods=["GET"]) 
@login_required
def take_test(test_id: int):
	test = db.session.get(Test, test_id)
	if not test or (not test.is_published and current_user.role == "student"):
		flash("Test not available", "danger")
		return redirect(url_for("main.dashboard"))
	# block if already attempted
	attempt = Result.query.filter_by(student_id=current_user.id, test_id=test.id).first()
	if attempt:
		flash("You have already attempted this test.", "warning")
		return redirect(url_for("tests.manage_tests"))
	return render_template("take_test.html", test=test)


@tests_bp.route("/submit_test/<int:test_id>", methods=["POST"]) 
@login_required
def submit_test(test_id: int):
	test = db.session.get(Test, test_id)
	if not test:
		flash("Test not found", "danger")
		return redirect(url_for("main.dashboard"))
	# prevent double submit
	attempt = Result.query.filter_by(student_id=current_user.id, test_id=test.id).first()
	if attempt:
		flash("You have already submitted this test.", "warning")
		return redirect(url_for("tests.manage_tests"))
	answers = {}
	for q in test.questions:
		answers[q.id] = request.form.get(f"q_{q.id}")
	correct = 0
	for q in test.questions:
		if answers.get(q.id) == q.correct:
			correct += 1
	# Build result with auto-grading
	meta = {"answers": answers}
	# Optional AI validation/feedback
	client = GeminiClient()
	if client.enabled:
		try:
			items = []
			for q in test.questions:
				items.append({
					"question": q.question,
					"options": [q.option1, q.option2, q.option3, q.option4],
					"correct": q.correct,
					"selected": answers.get(q.id),
				})
			import json
			prompt = (
				"For each MCQ, validate the student's selected answer and give a one-line explanation. "
				"Reply JSON with array 'feedback' of same order: [{correct: bool, note: string}]. Items: "
				+ json.dumps(items)
			)
			resp = client.model.generate_content(prompt)
			data = json.loads(resp.text or "{}")
			meta["feedback"] = data.get("feedback")
		except Exception:
			pass
	res = Result(student_id=current_user.id, test_id=test.id, subject=test.subject, marks=correct, total=len(test.questions), meta=meta)
	db.session.add(res)
	db.session.commit()
	flash(f"Test submitted. Score: {correct}/{len(test.questions)}", "success")
	return redirect(url_for("main.results"))


@tests_bp.route("/admin/upload", methods=["GET", "POST"]) 
@login_required
def upload_csv():
	if current_user.role not in ("admin", "teacher"):
		flash("Unauthorized", "danger")
		return redirect(url_for("main.dashboard"))
	if request.method == "POST":
		subject = request.form.get("subject")
		department = request.form.get("department")
		file = request.files.get("file")
		if not file:
			flash("No file uploaded", "danger")
			return redirect(url_for("tests.upload_csv"))
		test = Test(subject=subject, description="Uploaded test", created_by=current_user.id, department=department, is_published=True, ai_validated=True)
		db.session.add(test)
		db.session.flush()
		stream = TextIOWrapper(file.stream, encoding='utf-8')
		reader = csv.DictReader(stream)
		for row in reader:
			q = Question(
				test_id=test.id,
				question=row.get("question"),
				option1=row.get("option1"),
				option2=row.get("option2"),
				option3=row.get("option3"),
				option4=row.get("option4"),
				correct=row.get("correct"),
			)
			db.session.add(q)
		db.session.commit()
		flash("Test uploaded and published immediately.", "success")
		return redirect(url_for("tests.manage_tests"))
	return render_template("upload.html")
