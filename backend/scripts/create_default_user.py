import os
import sys
from sqlalchemy.orm import Session
from passlib.context import CryptContext

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import SessionLocal
from app.models.user import User, UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_default_user():
    db: Session = SessionLocal()
    try:
        # Check if the user already exists
        existing_user = db.query(User).filter(User.username == "recruiter").first()
        if existing_user:
            print("Default user 'recruiter' already exists.")
            return

        # Create a new user
        hashed_password = pwd_context.hash("password")
        new_user = User(
            username="recruiter",
            password_hash=hashed_password,
            role=UserRole.recruiter
        )
        db.add(new_user)
        db.commit()
        print("Default user 'recruiter' created successfully with password 'password'.")

    finally:
        db.close()

if __name__ == "__main__":
    create_default_user()
