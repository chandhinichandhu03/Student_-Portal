from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from ..extensions import db
from ..models import CodingProblem, TestCase, CodeSubmission
from ..services.gemini_client import GeminiClient
from ..services.code_executor import CodeExecutor
import json

coding_bp = Blueprint("coding", __name__)


@coding_bp.route("/coding")
@login_required
def coding_problems():
    """List all published coding problems"""
    problems = CodingProblem.query.filter_by(is_published=True).order_by(CodingProblem.created_at.desc()).all()
    return render_template("coding/problems.html", problems=problems)


@coding_bp.route("/coding/problem/<int:problem_id>")
@login_required
def view_problem(problem_id):
    """View a specific coding problem"""
    problem = db.session.get(CodingProblem, problem_id)
    if not problem or not problem.is_published:
        flash("Problem not found", "danger")
        return redirect(url_for("coding.coding_problems"))
    
    # Get user's previous submissions
    submissions = CodeSubmission.query.filter_by(
        student_id=current_user.id, 
        problem_id=problem_id
    ).order_by(CodeSubmission.submitted_at.desc()).limit(5).all()
    
    return render_template("coding/problem_detail.html", problem=problem, submissions=submissions)


@coding_bp.route("/coding/problem/<int:problem_id>/submit", methods=["POST"])
@login_required
def submit_solution(problem_id):
    """Submit a solution for a coding problem"""
    problem = db.session.get(CodingProblem, problem_id)
    if not problem or not problem.is_published:
        return jsonify({"error": "Problem not found"}), 404
    
    data = request.get_json()
    code = data.get('code', '').strip()
    language = data.get('language', 'python')
    
    if not code:
        return jsonify({"error": "Code cannot be empty"}), 400
    
    # Get test cases
    test_cases = TestCase.query.filter_by(problem_id=problem_id).all()
    if not test_cases:
        return jsonify({"error": "No test cases found"}), 400
    
    # Prepare test cases for execution
    test_case_data = []
    for tc in test_cases:
        test_case_data.append({
            'input': tc.input_data,
            'expected_output': tc.expected_output,
            'points': tc.points
        })
    
    # Execute code
    executor = CodeExecutor()
    result = executor.run_test_cases(
        code=code,
        language=language,
        test_cases=test_case_data,
        time_limit=problem.time_limit,
        memory_limit=problem.memory_limit
    )
    
    # Save submission
    submission = CodeSubmission(
        student_id=current_user.id,
        problem_id=problem_id,
        language=language,
        code=code,
        status=result['status'],
        execution_time=result['max_execution_time'],
        memory_used=result['max_memory_used'],
        score=result['score'],
        total_test_cases=result['total_test_cases'],
        passed_test_cases=result['passed_test_cases'],
        error_message=result.get('error_message', ''),
        test_results=result['test_results']
    )
    
    db.session.add(submission)
    db.session.commit()
    
    return jsonify({
        "status": result['status'],
        "score": result['score'],
        "passed_test_cases": result['passed_test_cases'],
        "total_test_cases": result['total_test_cases'],
        "execution_time": result['max_execution_time'],
        "memory_used": result['max_memory_used'],
        "test_results": result['test_results'],
        "submission_id": submission.id
    })


@coding_bp.route("/admin/coding")
@login_required
def admin_coding_problems():
    """Admin view of all coding problems"""
    if current_user.role not in ("admin", "teacher"):
        flash("Unauthorized", "danger")
        return redirect(url_for("main.dashboard"))
    
    problems = CodingProblem.query.order_by(CodingProblem.created_at.desc()).all()
    return render_template("coding/admin_problems.html", problems=problems)


@coding_bp.route("/admin/coding/create", methods=["GET", "POST"])
@login_required
def create_coding_problem():
    """Create a new coding problem"""
    if current_user.role not in ("admin", "teacher"):
        flash("Unauthorized", "danger")
        return redirect(url_for("main.dashboard"))
    
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        difficulty = request.form.get("difficulty")
        category = request.form.get("category")
        time_limit = int(request.form.get("time_limit", 5))
        memory_limit = int(request.form.get("memory_limit", 128))
        
        # Create problem
        problem = CodingProblem(
            title=title,
            description=description,
            difficulty=difficulty,
            category=category,
            time_limit=time_limit,
            memory_limit=memory_limit,
            created_by=current_user.id,
            is_published=True
        )
        
        db.session.add(problem)
        db.session.flush()
        
        # Add test cases
        test_case_inputs = request.form.getlist("test_case_input")
        test_case_outputs = request.form.getlist("test_case_output")
        test_case_points = request.form.getlist("test_case_points")
        
        for i, (input_data, output_data) in enumerate(zip(test_case_inputs, test_case_outputs)):
            if input_data.strip() and output_data.strip():
                test_case = TestCase(
                    problem_id=problem.id,
                    input_data=input_data.strip(),
                    expected_output=output_data.strip(),
                    points=int(test_case_points[i]) if test_case_points[i] else 10,
                    is_hidden=False
                )
                db.session.add(test_case)
        
        db.session.commit()
        flash("Coding problem created successfully!", "success")
        return redirect(url_for("coding.admin_coding_problems"))
    
    return render_template("coding/create_problem.html")


@coding_bp.route("/admin/coding/generate", methods=["GET", "POST"])
@login_required
def generate_coding_problem():
    """Generate coding problem using AI"""
    if current_user.role not in ("admin", "teacher"):
        flash("Unauthorized", "danger")
        return redirect(url_for("main.dashboard"))
    
    if request.method == "POST":
        topic = request.form.get("topic")
        difficulty = request.form.get("difficulty", "medium")
        category = request.form.get("category", "algorithms")
        num_test_cases = int(request.form.get("num_test_cases", 3))
        
        # Generate problem using AI
        client = GeminiClient()
        if not client.enabled:
            flash("AI service not available", "danger")
            return redirect(url_for("coding.create_coding_problem"))
        
        try:
            prompt = f"""
            Generate a coding problem with the following specifications:
            - Topic: {topic}
            - Difficulty: {difficulty}
            - Category: {category}
            - Number of test cases: {num_test_cases}
            
            Return a JSON response with the following structure:
            {{
                "title": "Problem title",
                "description": "Detailed problem description with examples",
                "test_cases": [
                    {{
                        "input": "input data",
                        "expected_output": "expected output",
                        "points": 10
                    }}
                ],
                "time_limit": 5,
                "memory_limit": 128
            }}
            
            Make sure the problem is clear, has good examples, and includes proper test cases.
            """
            
            response = client.model.generate_content(prompt)
            response_text = client._response_text(response)
            response_json = client._extract_json(response_text)
            
            data = json.loads(response_json)
            
            # Create problem
            problem = CodingProblem(
                title=data.get("title", f"Coding Problem: {topic}"),
                description=data.get("description", ""),
                difficulty=difficulty,
                category=category,
                time_limit=data.get("time_limit", 5),
                memory_limit=data.get("memory_limit", 128),
                created_by=current_user.id,
                is_published=True,
                ai_generated=True,
                ai_validation_notes="Generated by AI"
            )
            
            db.session.add(problem)
            db.session.flush()
            
            # Add test cases
            for test_case_data in data.get("test_cases", []):
                test_case = TestCase(
                    problem_id=problem.id,
                    input_data=test_case_data.get("input", ""),
                    expected_output=test_case_data.get("expected_output", ""),
                    points=test_case_data.get("points", 10),
                    is_hidden=False
                )
                db.session.add(test_case)
            
            db.session.commit()
            flash("AI-generated coding problem created successfully!", "success")
            return redirect(url_for("coding.admin_coding_problems"))
            
        except Exception as e:
            flash(f"Error generating problem: {str(e)}", "danger")
            return redirect(url_for("coding.create_coding_problem"))
    
    return render_template("coding/generate_problem.html")


@coding_bp.route("/coding/submissions")
@login_required
def my_submissions():
    """View user's coding submissions"""
    submissions = CodeSubmission.query.filter_by(student_id=current_user.id)\
        .order_by(CodeSubmission.submitted_at.desc()).all()
    return render_template("coding/submissions.html", submissions=submissions)


@coding_bp.route("/admin/coding/submissions")
@login_required
def admin_submissions():
    """Admin view of all coding submissions"""
    if current_user.role not in ("admin", "teacher"):
        flash("Unauthorized", "danger")
        return redirect(url_for("main.dashboard"))
    
    submissions = CodeSubmission.query.order_by(CodeSubmission.submitted_at.desc()).all()
    return render_template("coding/admin_submissions.html", submissions=submissions)


@coding_bp.route("/admin/coding/problem/<int:problem_id>/delete", methods=["POST"])
@login_required
def delete_coding_problem(problem_id: int):
    """Delete a coding problem"""
    if current_user.role not in ("admin", "teacher"):
        flash("Unauthorized", "danger")
        return redirect(url_for("main.dashboard"))
    
    problem = db.session.get(CodingProblem, problem_id)
    if not problem:
        flash("Problem not found", "danger")
        return redirect(url_for("coding.admin_coding_problems"))
    
    # Delete all test cases first
    TestCase.query.filter_by(problem_id=problem_id).delete()
    
    # Delete all submissions
    CodeSubmission.query.filter_by(problem_id=problem_id).delete()
    
    # Delete the problem
    db.session.delete(problem)
    db.session.commit()
    
    flash("Coding problem deleted successfully", "success")
    return redirect(url_for("coding.admin_coding_problems"))


@coding_bp.route("/admin/coding/problem/<int:problem_id>/regenerate", methods=["POST"])
@login_required
def regenerate_coding_problem(problem_id: int):
    """Regenerate a coding problem with new topic"""
    if current_user.role not in ("admin", "teacher"):
        flash("Unauthorized", "danger")
        return redirect(url_for("main.dashboard"))
    
    problem = db.session.get(CodingProblem, problem_id)
    if not problem:
        flash("Problem not found", "danger")
        return redirect(url_for("coding.admin_coding_problems"))
    
    # Get new topic from form
    new_topic = request.form.get("new_topic", problem.title).strip()
    difficulty = request.form.get("difficulty", "medium")
    category = request.form.get("category", "algorithms")
    
    if not new_topic:
        flash("Please enter a valid topic", "danger")
        return redirect(url_for("coding.admin_coding_problems"))
    
    try:
        # Delete existing test cases first and commit
        existing_test_cases = TestCase.query.filter_by(problem_id=problem_id).all()
        for tc in existing_test_cases:
            db.session.delete(tc)
        db.session.commit()
        
        # Regenerate problem using AI
        client = GeminiClient()
        if not client.enabled:
            flash("AI service not available", "danger")
            return redirect(url_for("coding.admin_coding_problems"))
        
        prompt = f"""
        Generate a coding problem with the following specifications:
        - Topic: {new_topic}
        - Difficulty: {difficulty}
        - Category: {category}
        
        Return a JSON object with:
        {{
            "title": "Problem title",
            "description": "Detailed problem description with examples",
            "constraints": "Input/output constraints",
            "examples": [
                {{"input": "example input", "output": "expected output", "explanation": "explanation"}}
            ],
            "test_cases": [
                {{"input": "test input", "output": "expected output", "points": 10}}
            ]
        }}
        
        Make sure the problem is clear, well-structured, and includes proper test cases.
        """
        
        response = client.model.generate_content(prompt)
        problem_data_text = client._extract_json(response.text)
        
        if not problem_data_text:
            flash("Failed to generate problem data", "danger")
            return redirect(url_for("coding.admin_coding_problems"))
        
        import json
        problem_data = json.loads(problem_data_text)
        
        if not problem_data:
            flash("Failed to parse problem data", "danger")
            return redirect(url_for("coding.admin_coding_problems"))
        
        # Update problem details
        problem.title = problem_data.get("title", new_topic)
        problem.description = problem_data.get("description", "")
        problem.constraints = problem_data.get("constraints", "")
        problem.difficulty = difficulty
        problem.category = category
        problem.ai_generated = True
        
        # Add test cases
        test_cases = problem_data.get("test_cases", [])
        if not test_cases:
            flash("No test cases generated", "danger")
            return redirect(url_for("coding.admin_coding_problems"))
        
        for i, test_case in enumerate(test_cases):
            tc = TestCase(
                problem_id=problem_id,
                input_data=test_case.get("input", ""),
                expected_output=test_case.get("output", ""),
                points=test_case.get("points", 10),
                is_hidden=i >= 2  # First 2 test cases are visible
            )
            db.session.add(tc)
        
        db.session.commit()
        flash(f"Coding problem regenerated successfully with {len(test_cases)} test cases on '{new_topic}'", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error regenerating problem: {str(e)}", "danger")
    
    return redirect(url_for("coding.admin_coding_problems"))
