from app import app, bcrypt, db
from models import Note, User


def seed():
    with app.app_context():
        db.create_all()
        db.session.query(Note).delete()
        db.session.query(User).delete()
        users = [
            User(username="brian", password_hash=bcrypt.generate_password_hash("password123").decode("utf-8")),
            User(username="yobby", password_hash=bcrypt.generate_password_hash("password123").decode("utf-8")),
        ]
        db.session.add_all(users)
        db.session.flush()
        db.session.add_all([
            Note(title="Welcome", content="This is Brian's private note.", user_id=users[0].id),
            Note(title="Plan", content="Remember to review the project goals.", user_id=users[0].id),
            Note(title="Ideas", content="Keep personal notes private by default.", user_id=users[1].id),
        ])
        db.session.commit()
        print("Seeded users brian and yobby (password: password123) with sample notes.")


if __name__ == "__main__":
    seed()
