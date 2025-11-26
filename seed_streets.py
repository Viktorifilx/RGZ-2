from app import db, Street, app

with app.app_context():
    streets = [
        ("Техно-улица", "it"),
        ("Арбат творчества", "design"),
        ("Аллея знаний", "study"),
        ("Аллея визуального кадра", "photo"),

        ("Киберпроспект", "cyber"),
        ("Переулок автоматизации", "automation"),
        ("Аллея алгоритмов", "algos"),
        ("Бульвар фронтенда", "frontend"),

        ("Улица интерфейсов", "uiux"),
        ("Пиксельный бульвар", "pixel"),
        ("Проспект вдохновения", "inspire"),
        ("Улица цифровой грамотности", "cheats"),
    ]

    for name, code in streets:
        exists = Street.query.filter_by(code=code).first()
        if not exists:
            db.session.add(Street(name=name, code=code))

    db.session.commit()

print("Все 12 улиц успешно созданы.")
