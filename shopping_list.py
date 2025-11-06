import pickle
import os

# FIXED: Added error handling for missing pickle file on first run
# FIXED: Using context manager (with statement) for proper file handling
def load_shopping_list():
    """Load shopping list from pickle file, create empty list if file doesn't exist"""
    if os.path.exists("shopping_list_file.pck"):
        try:
            with open("shopping_list_file.pck", "rb") as read_pickle_file:
                return pickle.load(read_pickle_file)
        except (pickle.UnpicklingError, EOFError) as e:
            print(f"Error loading file: {e}. Starting with empty list.")
            return []
    else:
        print("No existing shopping list found. Starting fresh!")
        return []


# FIXED: Added save functionality - this was completely missing in original code
def save_shopping_list(shopping_list):
    """Save shopping list to pickle file"""
    try:
        with open("shopping_list_file.pck", "wb") as write_pickle_file:
            pickle.dump(shopping_list, write_pickle_file)
        print("Shopping list saved successfully!")
    except Exception as e:
        print(f"Error saving file: {e}")


# Load the shopping list at startup
shopping_list = load_shopping_list()


def view_list():
    count = 1
    print()
    print("Shopping List")
    print("=" * 75)
    if len(shopping_list) == 0:
        print("Your shopping list is currently empty")  # FIXED: Minor grammar
    else:
        for item in shopping_list:
            print(f"{count}.\t{item.title()}")  # FIXED: Spacing consistency
            count += 1
    print()


# FIXED: Removed side effects (printing) from this function
# FIXED: Optimized - now breaks after finding item instead of continuing loop
# FIXED: Returns position directly instead of calling index() again
def find_in_list(f_item):
    """Check if item exists in list and return its position (1-indexed) or None"""
    for index, item in enumerate(shopping_list):
        if f_item.lower() == item.lower():  # FIXED: Case-insensitive comparison
            return index + 1  # Return 1-indexed position
    return None


# FIXED: Simplified this function using find_in_list()
def item_exist(f_item):
    """Check if item exists in the list (case-insensitive)"""
    return find_in_list(f_item) is not None


def add_to_list(a_item):
    """Add item to shopping list if it doesn't already exist"""
    # FIXED: Validate input
    if not a_item or a_item.strip() == "":
        print("Cannot add empty item!")
        return False

    a_item = a_item.strip()  # FIXED: Remove leading/trailing whitespace

    position = find_in_list(a_item)
    if position is None:
        shopping_list.append(a_item)
        print(f"'{a_item}' added to shopping list!")
        save_shopping_list(shopping_list)  # FIXED: Save after adding
        return True
    else:
        print(f"'{a_item}' is already in the list at position {position}")
        return False


# FIXED: Added error handling to prevent crashes when item doesn't exist
def delete_from_list(d_item):
    """Delete item from shopping list"""
    # FIXED: Check if item exists before trying to delete
    if not item_exist(d_item):
        print(f"'{d_item}' is not in the shopping list!")
        return False

    # FIXED: Case-insensitive search for deletion
    for index, item in enumerate(shopping_list):
        if d_item.lower() == item.lower():
            removed_item = shopping_list.pop(index)
            print(f"'{removed_item}' removed from shopping list!")
            save_shopping_list(shopping_list)  # FIXED: Save after deleting
            return True

    return False


# FIXED: Added function to display item position
def show_item_position(s_item):
    """Display the position of an item in the list"""
    position = find_in_list(s_item)
    if position:
        # Get the actual item from list to show proper casing
        actual_item = shopping_list[position - 1]
        print(f"'{actual_item}' is number {position} on the list")
    else:
        print(f"'{s_item}' is not in the shopping list")


# FIXED: Added main menu function for complete application
def main_menu():
    """Main menu for shopping list application"""
    while True:
        print("\n" + "=" * 75)
        print("SHOPPING LIST MANAGER")
        print("=" * 75)
        print("1. View shopping list")
        print("2. Add item")
        print("3. Delete item")
        print("4. Find item")
        print("5. Save and exit")
        print("=" * 75)

        choice = input("Enter your choice (1-5): ").strip()

        if choice == "1":
            view_list()

        elif choice == "2":
            item = input("Enter item to add: ").strip()
            add_to_list(item)

        elif choice == "3":
            view_list()
            item = input("Enter item to delete: ").strip()
            delete_from_list(item)

        elif choice == "4":
            item = input("Enter item to find: ").strip()
            show_item_position(item)

        elif choice == "5":
            save_shopping_list(shopping_list)
            print("\nThank you for using Shopping List Manager!")
            break

        else:
            print("Invalid choice! Please enter 1-5.")


# FIXED: Added proper entry point
if __name__ == "__main__":
    main_menu()
