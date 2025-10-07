import os
import subprocess
import tempfile
import time
import psutil
from typing import Dict, List, Tuple, Optional
import json


class CodeExecutor:
    """Handles code execution for multiple programming languages"""
    
    def __init__(self):
        self.supported_languages = {
            'python': {
                'extension': '.py',
                'command': 'python3',
                'compile_command': None,
                'timeout': 10
            },
            'java': {
                'extension': '.java',
                'command': 'java',
                'compile_command': 'javac',
                'timeout': 10
            },
            'cpp': {
                'extension': '.cpp',
                'command': './a.out',
                'compile_command': 'g++ -o a.out',
                'timeout': 10
            },
            'c': {
                'extension': '.c',
                'command': './a.out',
                'compile_command': 'gcc -o a.out',
                'timeout': 10
            },
            'javascript': {
                'extension': '.js',
                'command': 'node',
                'compile_command': None,
                'timeout': 10
            }
        }
    
    def execute_code(self, code: str, language: str, input_data: str = "", 
                    time_limit: int = 5, memory_limit: int = 128) -> Dict:
        """
        Execute code and return results
        
        Args:
            code: Source code to execute
            language: Programming language
            input_data: Input for the program
            time_limit: Time limit in seconds
            memory_limit: Memory limit in MB
            
        Returns:
            Dict with execution results
        """
        if language not in self.supported_languages:
            return {
                'status': 'error',
                'error_message': f'Unsupported language: {language}',
                'execution_time': 0,
                'memory_used': 0
            }
        
        try:
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Write code to file
                lang_config = self.supported_languages[language]
                code_file = os.path.join(temp_dir, f'main{lang_config["extension"]}')
                
                with open(code_file, 'w', encoding='utf-8') as f:
                    f.write(code)
                
                # Compile if needed
                if lang_config['compile_command']:
                    compile_result = self._compile_code(code_file, lang_config['compile_command'])
                    if compile_result['status'] != 'success':
                        return compile_result
                
                # Execute code
                return self._run_code(code_file, lang_config, input_data, time_limit, memory_limit)
                
        except Exception as e:
            return {
                'status': 'error',
                'error_message': f'Execution error: {str(e)}',
                'execution_time': 0,
                'memory_used': 0
            }
    
    def _compile_code(self, code_file: str, compile_command: str) -> Dict:
        """Compile code and return compilation result"""
        try:
            # Handle Java compilation (need to set classpath)
            if 'javac' in compile_command:
                # Extract class name from Java code
                with open(code_file, 'r') as f:
                    content = f.read()
                    if 'public class' in content:
                        class_name = content.split('public class ')[1].split()[0]
                        compile_command = f'javac -d . {code_file}'
            
            result = subprocess.run(
                compile_command.split(),
                cwd=os.path.dirname(code_file),
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return {
                    'status': 'compilation_error',
                    'error_message': result.stderr,
                    'execution_time': 0,
                    'memory_used': 0
                }
            
            return {'status': 'success'}
            
        except subprocess.TimeoutExpired:
            return {
                'status': 'compilation_error',
                'error_message': 'Compilation timeout',
                'execution_time': 0,
                'memory_used': 0
            }
        except Exception as e:
            return {
                'status': 'compilation_error',
                'error_message': f'Compilation error: {str(e)}',
                'execution_time': 0,
                'memory_used': 0
            }
    
    def _run_code(self, code_file: str, lang_config: Dict, input_data: str, 
                  time_limit: int, memory_limit: int) -> Dict:
        """Run compiled/interpreted code"""
        try:
            # Prepare command
            if lang_config['command'] == 'java':
                # Handle Java execution
                with open(code_file, 'r') as f:
                    content = f.read()
                    if 'public class' in content:
                        class_name = content.split('public class ')[1].split()[0]
                        command = ['java', class_name]
                    else:
                        command = ['java', 'Main']
            elif lang_config['command'] == './a.out':
                command = ['./a.out']
            else:
                command = [lang_config['command'], code_file]
            
            # Start process
            start_time = time.time()
            process = subprocess.Popen(
                command,
                cwd=os.path.dirname(code_file),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Monitor memory usage
            max_memory = 0
            try:
                # Send input and get output
                stdout, stderr = process.communicate(
                    input=input_data,
                    timeout=time_limit
                )
                
                # Calculate execution time
                execution_time = time.time() - start_time
                
                # Get memory usage
                try:
                    process_info = psutil.Process(process.pid)
                    max_memory = process_info.memory_info().rss / 1024 / 1024  # MB
                except:
                    max_memory = 0
                
                # Check if memory limit exceeded
                if max_memory > memory_limit:
                    return {
                        'status': 'memory_limit_exceeded',
                        'error_message': f'Memory limit exceeded: {max_memory:.2f}MB > {memory_limit}MB',
                        'execution_time': execution_time,
                        'memory_used': max_memory,
                        'output': stdout,
                        'error': stderr
                    }
                
                # Check return code
                if process.returncode != 0:
                    return {
                        'status': 'runtime_error',
                        'error_message': stderr or 'Runtime error',
                        'execution_time': execution_time,
                        'memory_used': max_memory,
                        'output': stdout,
                        'error': stderr
                    }
                
                return {
                    'status': 'success',
                    'output': stdout.strip(),
                    'execution_time': execution_time,
                    'memory_used': max_memory,
                    'error': stderr
                }
                
            except subprocess.TimeoutExpired:
                process.kill()
                return {
                    'status': 'time_limit_exceeded',
                    'error_message': f'Time limit exceeded: {time_limit}s',
                    'execution_time': time_limit,
                    'memory_used': max_memory
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error_message': f'Execution error: {str(e)}',
                'execution_time': 0,
                'memory_used': 0
            }
    
    def run_test_cases(self, code: str, language: str, test_cases: List[Dict], 
                      time_limit: int = 5, memory_limit: int = 128) -> Dict:
        """
        Run code against multiple test cases
        
        Args:
            code: Source code
            language: Programming language
            test_cases: List of test cases with 'input' and 'expected_output'
            time_limit: Time limit per test case
            memory_limit: Memory limit per test case
            
        Returns:
            Dict with overall results and individual test case results
        """
        results = []
        total_passed = 0
        total_score = 0
        max_execution_time = 0
        max_memory_used = 0
        
        for i, test_case in enumerate(test_cases):
            result = self.execute_code(
                code=code,
                language=language,
                input_data=test_case['input'],
                time_limit=time_limit,
                memory_limit=memory_limit
            )
            
            # Check if output matches expected
            passed = False
            if result['status'] == 'success':
                actual_output = result['output'].strip()
                expected_output = test_case['expected_output'].strip()
                passed = actual_output == expected_output
                
                if passed:
                    total_passed += 1
                    total_score += test_case.get('points', 10)
            
            # Track maximum execution time and memory
            max_execution_time = max(max_execution_time, result.get('execution_time', 0))
            max_memory_used = max(max_memory_used, result.get('memory_used', 0))
            
            # Store test case result
            test_result = {
                'test_case_id': i + 1,
                'status': result['status'],
                'passed': passed,
                'execution_time': result.get('execution_time', 0),
                'memory_used': result.get('memory_used', 0),
                'actual_output': result.get('output', ''),
                'expected_output': test_case['expected_output'],
                'error_message': result.get('error_message', ''),
                'points': test_case.get('points', 10) if passed else 0
            }
            
            results.append(test_result)
        
        # Determine overall status
        if total_passed == len(test_cases):
            overall_status = 'accepted'
        elif any(r['status'] in ['time_limit_exceeded', 'memory_limit_exceeded'] for r in results):
            overall_status = 'time_limit' if any(r['status'] == 'time_limit_exceeded' for r in results) else 'memory_limit'
        elif any(r['status'] in ['compilation_error', 'runtime_error'] for r in results):
            overall_status = 'runtime_error'
        else:
            overall_status = 'wrong_answer'
        
        return {
            'status': overall_status,
            'total_test_cases': len(test_cases),
            'passed_test_cases': total_passed,
            'score': total_score,
            'max_execution_time': max_execution_time,
            'max_memory_used': max_memory_used,
            'test_results': results
        }
