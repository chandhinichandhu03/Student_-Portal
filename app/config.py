import os
from dotenv import load_dotenv

load_dotenv()


class Config:
	SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
	SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///student_portal.db")
	SQLALCHEMY_TRACK_MODIFICATIONS = False
	FLASK_ENV = os.getenv("FLASK_ENV", "development")
	GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyBbPVM5AzKJI1ekeUXrQR2BvOgl2S9TLmE")
	DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL")
	DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD")

	# WebAuthn / Passkeys
	WEBAUTHN_RP_ID = os.getenv("WEBAUTHN_RP_ID", "localhost")
	WEBAUTHN_ORIGIN = os.getenv("WEBAUTHN_ORIGIN", "http://localhost:5000")
