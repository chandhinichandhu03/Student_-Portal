from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from ..extensions import db
from ..models import Test, Question, Result


api_bp = Blueprint("api", __name__)


@api_bp.get("/tests")
@login_required
def api_tests():
	items = Test.query.filter_by(is_published=True).all()
	return jsonify([
		{"id": t.id, "subject": t.subject, "time_limit": t.time_limit_minutes, "questions": len(t.questions)} for t in items
	])


@api_bp.get("/results")
@login_required
def api_results():
	items = Result.query.filter_by(student_id=current_user.id).all()
	return jsonify([
		{"id": r.id, "subject": r.subject, "score": r.marks, "total": r.total, "timestamp": r.timestamp.isoformat()} for r in items
	])





@api_bp.post("/tests")
@login_required
def api_create_test():
	if current_user.role not in ("admin", "teacher"):
		return jsonify({"error": "unauthorized"}), 403
	data = request.get_json(force=True)
	t = Test(subject=data.get("subject"), description=data.get("description"), created_by=current_user.id, department=data.get("department"), is_published=data.get("is_published", False))
	db.session.add(t)
	db.session.flush()
	for q in data.get("questions", []):
		db.session.add(Question(test_id=t.id, question=q["question"], option1=q["option1"], option2=q["option2"], option3=q["option3"], option4=q["option4"], correct=q["correct"]))
	db.session.commit()
	return jsonify({"id": t.id}), 201
