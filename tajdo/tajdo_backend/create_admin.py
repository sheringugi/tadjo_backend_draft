from app.db.session import SessionLocal
from app.models import models
import sys

def promote_to_admin(email: str):
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            print(f"Error: User with email '{email}' not found.")
            print("Please register the user via the API first.")
            return

        user.role = "admin"
        db.commit()
        print(f"Success! User '{email}' has been promoted to ADMIN.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    email_input = input("Enter the email address of the user to promote to Admin: ")
    promote_to_admin(email_input)