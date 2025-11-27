from app import app, db, User
from werkzeug.security import generate_password_hash


def create_admin():
    username = "Администратор"
    email = "admin@example.com"      
    password_plain = "12345"         

    with app.app_context():
        existing = User.query.filter_by(email=email).first()
        if existing:
            print("Администратор с таким email уже существует.")
            return

        admin = User(
            username=username,
            email=email,
            password = generate_password_hash(password_plain),
            role="admin"
        )
        db.session.add(admin)
        db.session.commit()
        print("Администратор создан.")
        print("Логин:", email)
        print("Пароль:", password_plain)


if __name__ == "__main__":
    create_admin()
