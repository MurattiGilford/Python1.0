#!/usr/bin/env python3
"""
Test script for the Marks to Grade System
"""

from marks_to_grade import GradeSystem, StudentGradeManager

def test_grade_system():
    """Test the grade conversion functionality"""
    print("Testing Grade System...")
    print("="*50)

    grade_system = GradeSystem()

    # Test cases
    test_cases = [
        (95, "A+"),
        (87, "A"),
        (82, "B+"),
        (76, "B"),
        (72, "C+"),
        (67, "C"),
        (55, "D"),
        (45, "F"),
        (100, "A+"),
        (0, "F"),
    ]

    print("\nTesting individual marks:")
    for marks, expected_grade in test_cases:
        grade = grade_system.get_grade(marks)
        status = grade_system.get_status(grade)
        result = "✓" if grade == expected_grade else "✗"
        print(f"{result} Marks: {marks:3} | Grade: {grade:3} | Expected: {expected_grade:3} | Status: {status}")

    print("\n" + "="*50)

def test_student_manager():
    """Test the student management functionality"""
    print("\nTesting Student Manager...")
    print("="*50)

    manager = StudentGradeManager()

    # Add test students
    test_students = [
        ("Alice Johnson", 92),
        ("Bob Smith", 78),
        ("Charlie Brown", 65),
        ("Diana Prince", 88),
        ("Eve Adams", 45),
    ]

    print("\nAdding students:")
    for name, marks in test_students:
        student = manager.add_student(name, marks)
        print(f"Added: {student.name} - Marks: {student.marks}, Grade: {student.grade}, Status: {student.status}")

    # Display all students
    manager.display_all_students()

    # Display statistics
    manager.get_statistics()

    print("="*50)

if __name__ == "__main__":
    print("\n" + "="*50)
    print("MARKS TO GRADE SYSTEM - TEST SUITE")
    print("="*50 + "\n")

    test_grade_system()
    test_student_manager()

    print("\n✓ All tests completed successfully!\n")
