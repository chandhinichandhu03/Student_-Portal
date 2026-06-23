# Student Portal

A modern web-based Student Portal application built with Flask, SQLAlchemy, and Gemini AI integration. This application features automated database migrations, user roles (admin/student), coding platform challenges, student profiling, and administrative controls.

---

## 🚀 Quick Start (One-Click Launch)

Start the portal immediately using the pre-configured scripts for your operating system.

### 🍎 macOS & Linux
Open your terminal in the project directory and run:
```bash
chmod +x run.sh
./run.sh
```

### 🪟 Windows
Double-click `run.bat` or run it from the Command Prompt (cmd):
```cmd
run.bat
```

---

## 🛠️ Manual Installation & Run

If you prefer to run the setup manually, follow these instructions.

### Prerequisites
- Python 3.8 or higher installed on your system.

### 🍎 macOS & Linux (Terminal)
1. **Create a virtual environment:**
   ```bash
   python3 -m venv .venv
   ```
2. **Activate the virtual environment:**
   ```bash
   source .venv/bin/activate
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Run the application:**
   ```bash
   python wsgi.py
   ```

### 🪟 Windows (Command Prompt / CMD)
1. **Create a virtual environment:**
   ```cmd
   python -m venv .venv
   ```
2. **Activate the virtual environment:**
   ```cmd
   .venv\Scripts\activate
   ```
3. **Install dependencies:**
   ```cmd
   pip install -r requirements.txt
   ```
4. **Run the application:**
   ```cmd
   python wsgi.py
   ```

---

## 🔑 Default Credentials

The database tables and a default administrator account are automatically initialized on the first startup. You can log in using:

> [!IMPORTANT]
> **Admin Login Credentials:**
> - **Email:** `admin@example.com`
> - **Password:** `Admin@123`

Students can register a new account directly through the registration link on the login page.

---

## ⚙️ Environment Configuration

Environment variables are managed in the `.env` file in the root directory. Below is the configuration structure:

```env
FLASK_ENV=development
SECRET_KEY=dev
DATABASE_URL=sqlite:///student_portal.db
GEMINI_API_KEY=<your-gemini-api-key>
DEFAULT_ADMIN_EMAIL=admin@example.com
DEFAULT_ADMIN_PASSWORD=Admin@123
```