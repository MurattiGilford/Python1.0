#!/usr/bin/env python3
"""
Simple Marks to Grade Student System
Converts numerical marks to letter grades for students
"""


class GradeSystem:
    """Handles conversion of marks to grades"""

    def __init__(self):
        # Define grading scale
        self.grading_scale = {
            'A+': (90, 100),
            'A': (85, 89),
            'B+': (80, 84),
            'B': (75, 79),
            'C+': (70, 74),
            'C': (65, 69),
            'D': (50, 64),
            'F': (0, 49)
        }

    def get_grade(self, marks):
        """
        Convert marks to grade

        Args:
            marks (float): Student's marks (0-100)

        Returns:
            str: Letter grade
        """
        if marks < 0 or marks > 100:
            return "Invalid marks! Must be between 0 and 100"

        for grade, (min_marks, max_marks) in self.grading_scale.items():
            if min_marks <= marks <= max_marks:
                return grade

        return "Invalid"

    def get_status(self, grade):
        """
        Determine if student passed or failed

        Args:
            grade (str): Letter grade

        Returns:
            str: Pass/Fail status
        """
        if grade == 'F' or grade == "Invalid":
            return "FAIL"
        return "PASS"

    def display_grading_scale(self):
        """Display the grading scale"""
        print("\n" + "="*50)
        print("GRADING SCALE")
        print("="*50)
        for grade, (min_marks, max_marks) in self.grading_scale.items():
            print(f"{grade:4} : {min_marks:3} - {max_marks:3} marks")
        print("="*50 + "\n")


class Student:
    """Represents a student with their marks"""

    def __init__(self, name, marks):
        self.name = name
        self.marks = marks
        self.grade = None
        self.status = None

    def __str__(self):
        return f"{self.name:20} | Marks: {self.marks:6.2f} | Grade: {self.grade:3} | Status: {self.status}"


class StudentGradeManager:
    """Manages multiple students and their grades"""

    def __init__(self):
        self.students = []
        self.grade_system = GradeSystem()

    def add_student(self, name, marks):
        """Add a student and calculate their grade"""
        student = Student(name, marks)
        student.grade = self.grade_system.get_grade(marks)
        student.status = self.grade_system.get_status(student.grade)
        self.students.append(student)
        return student

    def display_all_students(self):
        """Display all students with their grades"""
        if not self.students:
            print("\nNo students in the system yet!\n")
            return

        print("\n" + "="*70)
        print("STUDENT GRADE REPORT")
        print("="*70)
        print(f"{'Name':20} | {'Marks':6} | {'Grade':5} | {'Status':6}")
        print("-"*70)

        for student in self.students:
            print(student)

        print("="*70 + "\n")

    def get_statistics(self):
        """Display statistics about all students"""
        if not self.students:
            print("\nNo students in the system yet!\n")
            return

        total_students = len(self.students)
        passed = sum(1 for s in self.students if s.status == "PASS")
        failed = total_students - passed
        average = sum(s.marks for s in self.students) / total_students

        print("\n" + "="*50)
        print("STATISTICS")
        print("="*50)
        print(f"Total Students    : {total_students}")
        print(f"Passed           : {passed}")
        print(f"Failed           : {failed}")
        print(f"Pass Rate        : {(passed/total_students)*100:.2f}%")
        print(f"Average Marks    : {average:.2f}")
        print("="*50 + "\n")


def main():
    """Main function to run the grade system"""
    manager = StudentGradeManager()
    grade_system = GradeSystem()

    print("\n" + "="*50)
    print("WELCOME TO MARKS TO GRADE SYSTEM")
    print("="*50)

    while True:
        print("\n--- MENU ---")
        print("1. View Grading Scale")
        print("2. Add Student")
        print("3. View All Students")
        print("4. View Statistics")
        print("5. Check Single Mark")
        print("6. Exit")

        choice = input("\nEnter your choice (1-6): ").strip()

        if choice == '1':
            grade_system.display_grading_scale()

        elif choice == '2':
            try:
                name = input("Enter student name: ").strip()
                if not name:
                    print("Name cannot be empty!")
                    continue

                marks = float(input("Enter marks (0-100): ").strip())
                student = manager.add_student(name, marks)

                if "Invalid" in student.grade:
                    print(f"\n{student.grade}")
                else:
                    print(f"\nStudent added successfully!")
                    print(f"Name: {student.name}")
                    print(f"Marks: {student.marks}")
                    print(f"Grade: {student.grade}")
                    print(f"Status: {student.status}")

            except ValueError:
                print("\nInvalid input! Please enter a valid number for marks.")

        elif choice == '3':
            manager.display_all_students()

        elif choice == '4':
            manager.get_statistics()

        elif choice == '5':
            try:
                marks = float(input("Enter marks to check grade (0-100): ").strip())
                grade = grade_system.get_grade(marks)
                status = grade_system.get_status(grade)

                print(f"\nMarks: {marks}")
                print(f"Grade: {grade}")
                print(f"Status: {status}\n")

            except ValueError:
                print("\nInvalid input! Please enter a valid number.")

        elif choice == '6':
            print("\nThank you for using the Marks to Grade System!")
            print("Goodbye!\n")
            break

        else:
            print("\nInvalid choice! Please enter a number between 1 and 6.")


if __name__ == "__main__":
    main()
