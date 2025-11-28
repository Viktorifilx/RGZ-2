from app import app, db, User, Ad

with app.app_context():
    # берём только мастеров, пропуская админа
    masters = (
        User.query
        .filter(User.role == "master")
        .order_by(User.id)
        .all()
    )

    if not masters:
        print("Мастеров в БД нет.")
        exit()

    ads = Ad.query.order_by(Ad.id).all()

    i = 0
    for ad in ads:
        master = masters[i % len(masters)]
        ad.master_id = master.id
        ad.author_name = master.username   # чтобы имя в карточке совпадало с логином
        i += 1

    db.session.commit()
    print(f"Готово, распределили {len(ads)} объявлений между {len(masters)} мастерами.")
