# Marks to Grade Student System

A simple Python-based system to convert student marks (0-100) into letter grades with pass/fail status.

## Features

- ✅ Convert numerical marks to letter grades
- ✅ Manage multiple students
- ✅ View detailed grade reports
- ✅ Calculate statistics (pass rate, average, etc.)
- ✅ Interactive menu-driven interface
- ✅ Input validation

## Grading Scale

| Grade | Marks Range |
|-------|-------------|
| A+    | 90 - 100    |
| A     | 85 - 89     |
| B+    | 80 - 84     |
| B     | 75 - 79     |
| C+    | 70 - 74     |
| C     | 65 - 69     |
| D     | 50 - 64     |
| F     | 0 - 49      |

**Pass Requirement:** Grade D or above (50+ marks)

## Usage

### Running the Interactive System

```bash
python3 marks_to_grade.py
```

### Menu Options

1. **View Grading Scale** - Display the grading scale
2. **Add Student** - Add a new student with their marks
3. **View All Students** - Display all students and their grades
4. **View Statistics** - Show pass rate, average marks, etc.
5. **Check Single Mark** - Quickly check what grade a mark converts to
6. **Exit** - Exit the program

### Running Tests

```bash
python3 test_marks_system.py
```

## Example Usage

```python
from marks_to_grade import GradeSystem, StudentGradeManager

# Create a grade system
grade_system = GradeSystem()

# Get grade for a mark
grade = grade_system.get_grade(85)  # Returns 'A'

# Create a student manager
manager = StudentGradeManager()

# Add students
manager.add_student("John Doe", 92)
manager.add_student("Jane Smith", 78)

# Display all students
manager.display_all_students()

# Show statistics
manager.get_statistics()
```

## Class Structure

### `GradeSystem`
- Handles conversion of marks to grades
- Methods: `get_grade()`, `get_status()`, `display_grading_scale()`

### `Student`
- Represents a student with name, marks, grade, and status

### `StudentGradeManager`
- Manages multiple students
- Methods: `add_student()`, `display_all_students()`, `get_statistics()`

## Sample Output

```
======================================================================
STUDENT GRADE REPORT
======================================================================
Name                 | Marks  | Grade | Status
----------------------------------------------------------------------
Alice Johnson        | Marks:  92.00 | Grade: A+  | Status: PASS
Bob Smith            | Marks:  78.00 | Grade: B   | Status: PASS
Charlie Brown        | Marks:  65.00 | Grade: C   | Status: PASS
======================================================================

==================================================
STATISTICS
==================================================
Total Students    : 3
Passed           : 3
Failed           : 0
Pass Rate        : 100.00%
Average Marks    : 78.33
==================================================
```

## Requirements

- Python 3.6 or higher
- No external dependencies required

## Author

Created for the Python1.0 project
