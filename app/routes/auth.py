from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from ..extensions import db
from ..models import User, StudentProfile, FaceCredential
from flask import current_app, jsonify
import os, base64, json


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
	if request.method == "POST":
		name = request.form.get("name")
		email = request.form.get("email")
		department = request.form.get("department")
		roll_number = request.form.get("roll_number")
		password = request.form.get("password")
		if User.query.filter((User.email == email) | (User.roll_number == roll_number)).first():
			flash("Email or Roll number already registered", "danger")
			return redirect(url_for("auth.register"))
		user = User(name=name, email=email, department=department, roll_number=roll_number, role="student", password_hash="")
		user.set_password(password)
		db.session.add(user)
		db.session.flush()
		profile = StudentProfile(user_id=user.id)
		db.session.add(profile)
		db.session.commit()
		flash("Registration successful. Please login.", "success")
		return redirect(url_for("auth.login"))
	return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
	if request.method == "POST":
		identifier = request.form.get("identifier")  # email or roll
		password = request.form.get("password")
		user = User.query.filter((User.email == identifier) | (User.roll_number == identifier)).first()
		if not user or not user.check_password(password):
			flash("Invalid credentials", "danger")
			return redirect(url_for("auth.login"))
		login_user(user)
		flash("Logged in successfully", "success")
		return redirect(url_for("main.dashboard"))
	return render_template("login.html")


@auth_bp.post("/face/enroll")
@login_required
def face_enroll():
	# Expect JSON: { embedding: [..] }
	data = request.get_json(force=True)
	emb = data.get("embedding")
	if not isinstance(emb, list) or not emb:
		return {"error": "invalid_embedding"}, 400
	# Replace existing
	existing = FaceCredential.query.filter_by(user_id=current_user.id).first()
	if existing:
		existing.embedding = emb
	else:
		fc = FaceCredential(user_id=current_user.id, embedding=emb)
		db.session.add(fc)
	db.session.commit()
	return {"ok": True}


@auth_bp.post("/face/login")
def face_login():
	# Expect JSON: { identifier, embedding }
	data = request.get_json(force=True)
	identifier = data.get("identifier")
	probe = data.get("embedding")
	if not identifier or not isinstance(probe, list):
		return {"error": "invalid"}, 400
	user = User.query.filter((User.email == identifier) | (User.roll_number == identifier)).first()
	if not user:
		return {"error": "user_not_found"}, 404
	fc = FaceCredential.query.filter_by(user_id=user.id).first()
	if not fc:
		return {"error": "no_face"}, 404
	# Cosine similarity
	import math
	def dot(a,b): return sum(x*y for x,y in zip(a,b))
	def norm(a): return math.sqrt(sum(x*x for x in a))
	s = dot(fc.embedding, probe) / (norm(fc.embedding) * norm(probe) + 1e-9)
	if s >= 0.85:
		login_user(user)
		return {"ok": True, "redirect": url_for('main.dashboard')}
	return {"error": "no_match"}, 401


# removed webauthn endpoints


@auth_bp.route("/logout")
@login_required
def logout():
	logout_user()
	flash("Logged out", "info")
	return redirect(url_for("auth.login"))
