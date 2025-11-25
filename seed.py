from app import db, Ad, Street, app

with app.app_context():
    it = Street.query.filter_by(code="it").first()
    design = Street.query.filter_by(code="design").first()
    study = Street.query.filter_by(code="study").first()
    photo = Street.query.filter_by(code="photo").first()

    ads = [
        Ad(
            title="Помогу с Python и SQL",
            text="Разберёмся с лабораторными, объясню теорию простым языком.",
            author_name="Иван",
            street_id=it.id
        ),
        Ad(
            title="Сделаю дизайн презентации",
            text="Подготовлю стильный макет под защиту или мероприятие.",
            author_name="Мария",
            street_id=design.id
        ),
        Ad(
            title="Подготовлю к зачёту по экономике",
            text="Разберём задачи, примеры, дам мини-конспект.",
            author_name="Алексей",
            street_id=study.id
        ),
        Ad(
            title="Фотосессия для аватара",
            text="Обработка, помощь с позами, стильный результат.",
            author_name="Софья",
            street_id=photo.id
        ),
    ]

    db.session.add_all(ads)
    db.session.commit()

print("Готово! Объявления добавлены.")

STREETS_DATA = [
    ("Техно-улица", "it"),
    ("Арбат творчества", "design"),
    ("Аллея знаний", "study"),
    ("Светлая улица", "photo"),

    ("Кодовый переулок", "code"),
    ("Дизайн-квартал", "design2"),
    ("Медиа-бульвар", "media"),
    ("Аналитический проспект", "analytics"),
    ("Маркетинговый проезд", "marketing"),
    ("Проджект-аллея", "project"),
    ("Startup-площадь", "startup"),
    ("Data-набережная", "data"),
]

ADS_DATA = [
    # Техно-улица
    ("Помогу с Python и SQL",
     "Разберёмся с лабораторными, объясню теорию простым языком.",
     "Иван", "it"),
    ("Разбор Flask/Django-проектов",
     "Помогу починить ошибки в коде, настроить роуты и базу данных.",
     "Кирилл", "it"),

    # Арбат творчества
    ("Сделаю дизайн презентации",
     "Подготовлю стильный макет под защиту или мероприятие.",
     "Мария", "design"),
    ("Оформление постов и сторис",
     "Делаю обложки, шаблоны и сторис в едином визуальном стиле.",
     "Алина", "design"),

    # Аллея знаний
    ("Подготовлю к зачёту по экономике",
     "Разберём задачи, примеры, дам мини-конспект.",
     "Алексей", "study"),
    ("Репетитор по высшей математике",
     "Объясню интегралы, ряды и линал без боли.",
     "Дмитрий", "study"),

    # Светлая улица
    ("Фотосессия для аватара",
     "Обработка, помощь с позами, стильный результат.",
     "Софья", "photo"),
    ("Обработка фотографий",
     "Цветокор, ретушь, подготовка к соцсетям и печати.",
     "Полина", "photo"),

    # Кодовый переулок
    ("Помощь с курсовым проектом по программированию",
     "Разберём архитектуру, напишем сложные функции, оформим код.",
     "Никита", "code"),

    # Дизайн-квартал
    ("Логотип и фирменный стиль",
     "Помогу придумать название, логотип и базовый брендбук.",
     "Екатерина", "design2"),

    # Медиа-бульвар
    ("Настройка и оформление Telegram-канала",
     "Шапка, описание, рубрики, базовый контент-план.",
     "Сергей", "media"),

    # Аналитический проспект
    ("Дашборды в Power BI / Excel",
     "Соберу отчёты, визуализации и интерактивные графики.",
     "Анна", "analytics"),

    # Маркетинговый проезд
    ("Аудит профиля в Instagram*",
     "Разберём шапку, визуал, тексты и воронку продаж.",
     "Вероника", "marketing"),

    # Проджект-аллея
    ("Помогу организовать учебный или пет-проект",
     "Сделаем план задач, декомпозицию и трекер в Trello / Notion.",
     "Глеб", "project"),

    # Startup-площадь
    ("Консультация по презентации стартапа",
     "Помогу упаковать идею под питч или хакатон.",
     "Роман", "startup"),

    # Data-набережная
    ("SQL и базы данных с нуля",
     "Разберём SELECT, JOIN, группировки на примерах из учёбы.",
     "Виктория", "data"),
]


def seed():
    with app.app_context():
        # 1. Улицы
        code_to_street = {}

        for name, code in STREETS_DATA:
            street = Street.query.filter_by(code=code).first()
            if not street:
                street = Street(name=name, code=code)
                db.session.add(street)
            code_to_street[code] = street

        db.session.flush()  # чтобы у новых улиц появились id

        # 2. Объявления
        added_count = 0
        for title, text, author_name, street_code in ADS_DATA:
            street = code_to_street.get(street_code)
            if not street:
                continue  # на всякий случай

            # чтобы не плодить дубли при повторном запуске
            existing = Ad.query.filter_by(
                title=title,
                author_name=author_name,
                street_id=street.id
            ).first()

            if existing:
                continue

            ad = Ad(
                title=title,
                text=text,
                author_name=author_name,
                street_id=street.id
            )
            db.session.add(ad)
            added_count += 1

        db.session.commit()
        print(f"Готово! Добавлено объявлений: {added_count}")


if __name__ == "__main__":
    seed()