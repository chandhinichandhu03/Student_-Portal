

from flask import Flask
from .config import Config
from .extensions import db, login_manager
from .models import User, StudentProfile, Test, Question, Result, Attendance, LeaveApplication, FeePayment, CodingProblem, TestCase, CodeSubmission
import json


def create_app(config_class: type = Config) -> Flask:
	app = Flask(__name__)
	app.config.from_object(config_class)

	# Initialize extensions
	db.init_app(app)
	login_manager.init_app(app)
	
	# Custom template filters
	@app.template_filter('from_json')
	def from_json_filter(value):
		if not value:
			return []
		try:
			return json.loads(value)
		except (json.JSONDecodeError, TypeError):
			return []

	@login_manager.user_loader
	def load_user(user_id: str):
		return db.session.get(User, int(user_id))

	with app.app_context():
		# Create tables if not exist
		db.create_all()
		# Schema migrations
		from .utils import ensure_default_admin, migrate_schema
		ensure_default_admin()
		migrate_schema()

	# Register blueprints
	from .routes.auth import auth_bp
	from .routes.main import main_bp
	from .routes.tests import tests_bp
	from .routes.admin import admin_bp
	from .routes.api import api_bp
	from .routes.coding import coding_bp

	app.register_blueprint(auth_bp)
	app.register_blueprint(main_bp)
	app.register_blueprint(tests_bp)
	app.register_blueprint(admin_bp)
	app.register_blueprint(api_bp, url_prefix="/api")
	app.register_blueprint(coding_bp)

	return app
