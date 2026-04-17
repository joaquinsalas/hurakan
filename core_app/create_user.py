from extensions import db
from models import User
from app import create_app

def create_user(username, password):
    app = create_app()

    with app.app_context():
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            print(f"User '{username}' already exists")
            return

        user = User(username=username)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        print(f"User '{username}' created successfully")
        
def delete_user(username):
    app = create_app()

    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"User '{username}' does not exist")
            return

        db.session.delete(user)
        db.session.commit()

        print(f"User '{username}' deleted successfully")

def menu():
    print("1. Create user")
    print("2. Delete user")
    choice = input("Select an option: ")

    if choice == '1':
        username = input("Username: ")
        password = input("Password: ")
        create_user(username, password)
    elif choice == '2':
        username = input("Username to delete: ")
        delete_user(username)
    else:
        print("Invalid option")

if __name__ == "__main__":
    menu()