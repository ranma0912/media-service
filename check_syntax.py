#!/usr/bin/env python
import os
import py_compile
import sys

def check_python_syntax(directory):
    errors = []
    checked_files = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                checked_files.append(filepath)
                try:
                    py_compile.compile(filepath, doraise=True)
                except py_compile.PyCompileError as e:
                    errors.append(f"Syntax error in {filepath}:\n{e}")
                except Exception as e:
                    errors.append(f"Error checking {filepath}: {e}")
    
    return checked_files, errors

def main():
    print("=" * 60)
    print("Python Syntax Check Report")
    print("=" * 60)
    
    # Check backend
    print("\n📂 Checking Python files in 'app/' directory...")
    checked_files, errors = check_python_syntax('app')
    
    # Check scripts
    print("📂 Checking Python files in 'scripts/' directory...")
    script_files, script_errors = check_python_syntax('scripts')
    checked_files.extend(script_files)
    errors.extend(script_errors)
    
    # Check tests
    print("📂 Checking Python files in 'tests/' directory...")
    test_files, test_errors = check_python_syntax('tests')
    checked_files.extend(test_files)
    errors.extend(test_errors)
    
    # Check root Python files
    print("📂 Checking Python files in root directory...")
    root_files = []
    for file in os.listdir('.'):
        if file.endswith('.py') and not file.startswith('check_syntax'):
            root_files.append(file)
    
    for file in root_files:
        checked_files.append(file)
        try:
            py_compile.compile(file, doraise=True)
        except py_compile.PyCompileError as e:
            errors.append(f"Syntax error in {file}:\n{e}")
        except Exception as e:
            errors.append(f"Error checking {file}: {e}")
    
    # Print results
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"✅ Total files checked: {len(checked_files)}")
    print(f"❌ Syntax errors found: {len(errors)}")
    
    if errors:
        print("\n" + "=" * 60)
        print("Detailed Errors")
        print("=" * 60)
        for error in errors:
            print(f"\n{error}\n{'-' * 60}")
        return 1
    else:
        print("\n✅ All Python files passed syntax check!")
        return 0

if __name__ == "__main__":
    sys.exit(main())