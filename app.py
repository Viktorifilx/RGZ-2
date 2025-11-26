from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__)

# секретный ключ для сессий и flash-сообщений
app.secret_key = "super_secret_key_change_me"

# --------- Абсолютный путь к БД ---------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "fair.db")
DB_URI = "sqlite:///" + DB_PATH.replace("\\", "/")

app.config["SQLALCHEMY_DATABASE_URI"] = DB_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# ---------- МОДЕЛИ ----------

class Street(db.Model):
    __tablename__ = 'streets'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(50), nullable=False, unique=True)  # it / design / study / photo и т.п.


class Pavilion(db.Model):
    __tablename__ = 'pavilions'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)

    street_id = db.Column(db.Integer, db.ForeignKey('streets.id'), nullable=False)
    street = db.relationship('Street', backref='pavilions')


class Ad(db.Model):
    __tablename__ = 'ads'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False)
    text = db.Column(db.Text, nullable=False)
    author_name = db.Column(db.String(120), nullable=False)
    master_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)


    pavilion_id = db.Column(db.Integer, db.ForeignKey('pavilions.id'), nullable=False)
    pavilion = db.relationship('Pavilion', backref='ads')


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), nullable=False)          # логин / ник
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)          # тут лежит ХЕШ
    role = db.Column(db.String(20), nullable=False, default="user")  # user / master / admin



class StreetRequest(db.Model):
    __tablename__ = 'street_requests'
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref='street_requests')

    street_name = db.Column(db.String(120), nullable=False)
    street_code = db.Column(db.String(50), nullable=False)
    pavilion_title = db.Column(db.String(150), nullable=False)
    pavilion_desc = db.Column(db.Text, nullable=True)

    status = db.Column(db.String(20), nullable=False, default="pending")  # pending / approved / rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # если заявка одобрена, сюда можно записать id созданной улицы
    street_id = db.Column(db.Integer, db.ForeignKey('streets.id'), nullable=True)


class AdRequest(db.Model):
    __tablename__ = "ad_requests"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("User", backref="ad_requests")

    pavilion_id = db.Column(db.Integer, db.ForeignKey("pavilions.id"), nullable=False)
    pavilion = db.relationship("Pavilion", backref="ad_requests")

    title = db.Column(db.String(250), nullable=False)
    text = db.Column(db.Text, nullable=False)

    status = db.Column(db.String(20), nullable=False, default="pending")  # pending / approved / rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SupportMessage(db.Model):
    __tablename__ = 'support_messages'
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref='support_messages')

    subject = db.Column(db.String(200), nullable=False)
    text = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="new")  # new / done
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # НОВОЕ:
    admin_reply = db.Column(db.Text, nullable=True)          # текст ответа админа
    replied_at = db.Column(db.DateTime, nullable=True) 

class AdMessage(db.Model):
    __tablename__ = "ad_messages"

    id = db.Column(db.Integer, primary_key=True)
    ad_id = db.Column(db.Integer, db.ForeignKey("ads.id"), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    is_read = db.Column(db.Boolean, default=False)




# ---------- СОЗДАНИЕ ТАБЛИЦ ----------

with app.app_context():
    db.create_all()


# ---------- ВСПОМОГАТЕЛЬНОЕ ----------

def get_student_info():
    return "Филатова Виктория", "ФБИ-34"


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Нужно войти на сайт, чтобы продолжить.", "error")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped


def admin_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if session.get("user_role") != "admin":
            flash("Доступ только для администратора.", "error")
            return redirect(url_for("index"))
        return view_func(*args, **kwargs)
    return wrapped


# ---------- МАРШРУТЫ САЙТА (ПОЛЬЗОВАТЕЛЬ) ----------

@app.route("/")
def index():
    # если админ — отправляем в админку
    if session.get("user_role") == "admin":
        return redirect(url_for("admin_dashboard"))

    streets = Street.query.order_by(Street.id).all()
    featured_ads = Ad.query.limit(12).all()
    fio, group = get_student_info()

    return render_template(
        "index.html",
        streets=streets,
        featured_ads=featured_ads,
        fio=fio,
        group=group
    )


@app.route("/street/<code>")
def street_page(code):
    street = Street.query.filter_by(code=code).first_or_404()
    pavilions = Pavilion.query.filter_by(street_id=street.id).order_by(Pavilion.id).all()

    fio, group = get_student_info()
    return render_template(
        "street.html",
        street=street,
        pavilions=pavilions,
        fio=fio,
        group=group
    )


@app.route("/pavilion/<int:pavilion_id>")
def pavilion_page(pavilion_id):
    pavilion = Pavilion.query.get_or_404(pavilion_id)
    ads = pavilion.ads

    fio, group = get_student_info()
    return render_template(
        "pavilion.html",
        pavilion=pavilion,
        ads=ads,
        fio=fio,
        group=group
    )


# ---------- ПРЕДЛОЖИТЬ ОБЪЯВЛЕНИЕ В ПАВИЛЬОН ----------

@app.route("/pavilion/<int:pavilion_id>/offer", methods=["GET", "POST"])
@login_required
def offer_ad(pavilion_id):
    fio, group = get_student_info()
    pavilion = Pavilion.query.get_or_404(pavilion_id)

    # только мастера и админ
    if session.get("user_role") not in ("master", "admin"):
        flash("Предлагать объявления могут только мастера.", "error")
        return redirect(url_for("pavilion_page", pavilion_id=pavilion_id))

    form = {"title": "", "text": ""}
    errors = []

    if request.method == "POST":
        form["title"] = request.form.get("title", "").strip()
        form["text"] = request.form.get("text", "").strip()

        if not form["title"]:
            errors.append("Введите заголовок объявления.")
        if not form["text"]:
            errors.append("Опишите, чем вы можете помочь.")

        if not errors:
            req = AdRequest(
                user_id=session["user_id"],
                pavilion_id=pavilion.id,
                title=form["title"],
                text=form["text"],
                status="pending"
            )
            db.session.add(req)
            db.session.commit()

            flash("Заявка на объявление отправлена администратору.", "success")
            return redirect(url_for("pavilion_page", pavilion_id=pavilion.id))

    return render_template(
        "offer_ad.html",
        pavilion=pavilion,
        form=form,
        errors=errors,
        fio=fio,
        group=group
    )


@app.route("/ad/<int:ad_id>")
def ad_page(ad_id):
    ad = Ad.query.get_or_404(ad_id)
    fio, group = get_student_info()
    return render_template(
        "ad.html",
        ad=ad,
        fio=fio,
        group=group
    )


# ---------- АВТОРИЗАЦИЯ / РЕГИСТРАЦИЯ ----------


from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, session, flash
# ... остальной код и модели


@app.route("/register", methods=["GET", "POST"])
def register():
    errors = []

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "user")

        if not username:
            errors.append("Введите логин.")
        if not email:
            errors.append("Введите e-mail.")
        if not password:
            errors.append("Введите пароль.")
        if User.query.filter_by(email=email).first():
            errors.append("Пользователь с таким e-mail уже существует.")

        if not errors:
            user = User(
                username=username,
                email=email,
                password=generate_password_hash(password),
                role=role
            )
            db.session.add(user)
            db.session.commit()
            # после успешной регистрации — на страницу входа
            return redirect(url_for("login"))

    return render_template("register.html", errors=errors)



from flask import render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash

@app.route("/login", methods=["GET", "POST"])
def login():
    errors = []

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()

        if user is None:
            errors.append("Пользователь с таким логином не найден.")
        else:
            # пробуем как с хешём (нормальный путь)
            ok = False
            try:
                if check_password_hash(user.password, password):
                    ok = True
            except ValueError:
                # на всякий случай — если в базе вдруг лежит голый пароль
                if user.password == password:
                    ok = True

            if not ok:
                errors.append("Неверный пароль.")

        if not errors and user:
            session["user_id"] = user.id
            session["username"] = user.username
            session["user_role"] = user.role
            return redirect(url_for("index"))

    return render_template("login.html", errors=errors)





@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ---------- СТРАНИЦА "КАК УСТРОЕНА ЯРМАРКА" ----------

@app.route("/how-it-works")
def how_it_works():
    fio, group = get_student_info()
    return render_template("how_it_works.html", fio=fio, group=group)

@app.route("/about")
def about():
    fio, group = get_student_info()
    return render_template("about.html", fio=fio, group=group)



# ---------- ЗАПРОС НОВОЙ УЛИЦЫ ----------

@app.route("/street/request", methods=["GET", "POST"])
@login_required
def request_street():
    fio, group = get_student_info()

    # только мастера и админ могут предлагать новые улицы
    if session.get("user_role") not in ("master", "admin"):
        flash("Предлагать новые улицы могут только мастера.", "error")
        return redirect(url_for("index"))

    form = {
        "street_name": "",
        "street_code": "",
        "pavilion_title": "",
        "pavilion_desc": "",
    }
    errors = []

    if request.method == "POST":
        form["street_name"] = request.form.get("street_name", "").strip()
        form["street_code"] = request.form.get("street_code", "").strip()
        form["pavilion_title"] = request.form.get("pavilion_title", "").strip()
        form["pavilion_desc"] = request.form.get("pavilion_desc", "").strip()

        if not form["street_name"]:
            errors.append("Введите название улицы.")
        if not form["street_code"]:
            errors.append("Укажите код улицы латиницей (например: techno_help).")
        else:
            cleaned = form["street_code"].replace("_", "")
            if not cleaned.isalnum() or not form["street_code"].islower():
                errors.append(
                    "Код можно только строчными латинскими буквами, цифрами и подчёркиваниями."
                )
            else:
                exists = Street.query.filter_by(code=form["street_code"]).first()
                if exists:
                    errors.append("Такой код улицы уже занят, попробуйте другой.")

        if not form["pavilion_title"]:
            errors.append("Введите название первого павильона.")

        if not errors:
            req = StreetRequest(
                user_id=session["user_id"],
                street_name=form["street_name"],
                street_code=form["street_code"],
                pavilion_title=form["pavilion_title"],
                pavilion_desc=form["pavilion_desc"],
                status="pending"
            )
            db.session.add(req)
            db.session.commit()

            flash("Заявка отправлена администратору. После одобрения улица появится на ярмарке.", "success")
            return redirect(url_for("index"))

    return render_template(
        "street_request.html",
        fio=fio,
        group=group,
        form=form,
        errors=errors
    )


# ---------- ПОДДЕРЖКА ----------

@app.route("/support", methods=["GET", "POST"])
@login_required
def support():
    fio, group = get_student_info()
    errors = []

    if request.method == "POST":
        subject = request.form.get("subject", "").strip()
        text = request.form.get("text", "").strip()

        if not subject:
            errors.append("Напишите тему сообщения.")
        if not text:
            errors.append("Напишите текст обращения.")

        if not errors:
            msg = SupportMessage(
                user_id=session["user_id"],
                subject=subject,
                text=text,
                status="new"
            )
            db.session.add(msg)
            db.session.commit()
            flash("Сообщение отправлено администратору.", "success")
            return redirect(url_for("support"))

    # НОВОЕ: выбираем последние сообщения этого пользователя
    my_messages = SupportMessage.query.filter_by(
        user_id=session["user_id"]
    ).order_by(SupportMessage.created_at.desc()).limit(10).all()

    return render_template(
        "support.html",
        fio=fio,
        group=group,
        errors=errors,
        my_messages=my_messages   # НОВЫЙ параметр в шаблон
    )


# ---------- АДМИН: ГЛАВНАЯ ПАНЕЛЬ ----------

@app.route("/admin")
@admin_required
def admin_dashboard():
    fio, group = get_student_info()
    streets = Street.query.order_by(Street.id).all()
    return render_template(
        "admin_dashboard.html",
        fio=fio,
        group=group,
        streets=streets
    )


# ---------- АДМИН: ЗАЯВКИ НА УЛИЦЫ ----------

@app.route("/admin/requests")
@admin_required
def admin_requests():
    fio, group = get_student_info()
    requests_list = StreetRequest.query.order_by(StreetRequest.created_at.desc()).all()

    stats = {
        "total": len(requests_list),
        "pending": sum(1 for r in requests_list if r.status == "pending"),
        "approved": sum(1 for r in requests_list if r.status == "approved"),
        "rejected": sum(1 for r in requests_list if r.status == "rejected"),
    }

    return render_template(
        "admin_requests.html",
        fio=fio,
        group=group,
        requests=requests_list,
        stats=stats
    )


@app.route("/admin/requests/<int:req_id>/approve", methods=["POST"])
@admin_required
def approve_request(req_id):
    req = StreetRequest.query.get_or_404(req_id)

    if req.status != "pending":
        flash("Эта заявка уже обработана.", "error")
        return redirect(url_for("admin_requests"))

    new_street = Street(name=req.street_name, code=req.street_code)
    db.session.add(new_street)
    db.session.flush()

    pav = Pavilion(
        title=req.pavilion_title,
        description=req.pavilion_desc,
        street=new_street
    )
    db.session.add(pav)

    req.status = "approved"
    req.street_id = new_street.id

    db.session.commit()

    flash("Улица и первый павильон созданы.", "success")
    return redirect(url_for("street_page", code=new_street.code))


@app.route("/admin/requests/<int:req_id>/reject", methods=["POST"])
@admin_required
def reject_request(req_id):
    req = StreetRequest.query.get_or_404(req_id)

    if req.status != "pending":
        flash("Эта заявка уже обработана.", "error")
    else:
        req.status = "rejected"
        db.session.commit()
        flash("Заявка отклонена.", "info")

    return redirect(url_for("admin_requests"))


# ---------- АДМИН: СООБЩЕНИЯ В ПОДДЕРЖКУ ----------

@app.route("/admin/support")
@admin_required
def admin_support():
    fio, group = get_student_info()
    messages = SupportMessage.query.order_by(SupportMessage.created_at.desc()).all()

    stats = {
        "total": len(messages),
        "new": sum(1 for m in messages if m.status == "new"),
        "done": sum(1 for m in messages if m.status == "done"),
    }

    return render_template(
        "admin_support.html",
        fio=fio,
        group=group,
        messages=messages,
        stats=stats
    )


@app.route("/admin/support/<int:msg_id>/close", methods=["POST"])
@admin_required
def close_support(msg_id):
    msg = SupportMessage.query.get_or_404(msg_id)
    msg.status = "done"
    db.session.commit()
    flash("Обращение помечено как обработанное.", "success")
    return redirect(url_for("admin_support"))


# ---------- АДМИН: УПРАВЛЕНИЕ ПАВИЛЬОНАМИ/ОБЪЯВЛЕНИЯМИ ----------

@app.route("/admin/pavilion/<int:pavilion_id>/clear", methods=["POST"])
@admin_required
def admin_clear_pavilion(pavilion_id):
    pavilion = Pavilion.query.get_or_404(pavilion_id)

    Ad.query.filter_by(pavilion_id=pavilion.id).delete()
    db.session.commit()

    flash("Все объявления в павильоне удалены.", "success")
    return redirect(url_for("pavilion_page", pavilion_id=pavilion.id))


@app.route("/admin/pavilion/<int:pavilion_id>/delete", methods=["POST"])
@admin_required
def admin_delete_pavilion(pavilion_id):
    pavilion = Pavilion.query.get_or_404(pavilion_id)
    street_code = pavilion.street.code

    Ad.query.filter_by(pavilion_id=pavilion.id).delete()
    db.session.delete(pavilion)
    db.session.commit()

    flash("Павильон удалён.", "success")
    return redirect(url_for("street_page", code=street_code))


@app.route("/admin/ad/<int:ad_id>/delete", methods=["POST"])
@admin_required
def admin_delete_ad(ad_id):
    ad = Ad.query.get_or_404(ad_id)
    pavilion_id = ad.pavilion_id

    db.session.delete(ad)
    db.session.commit()

    flash("Объявление удалено.", "success")
    return redirect(url_for("pavilion_page", pavilion_id=pavilion_id))


# ---------- АДМИН: ЗАЯВКИ НА ОБЪЯВЛЕНИЯ ----------

@app.route("/admin/ad-requests")
@admin_required
def admin_ad_requests():
    fio, group = get_student_info()
    requests_list = AdRequest.query.order_by(AdRequest.created_at.desc()).all()

    stats = {
        "total": len(requests_list),
        "pending": sum(1 for r in requests_list if r.status == "pending"),
        "approved": sum(1 for r in requests_list if r.status == "approved"),
        "rejected": sum(1 for r in requests_list if r.status == "rejected"),
    }

    return render_template(
        "admin_ad_requests.html",
        fio=fio,
        group=group,
        requests=requests_list,
        stats=stats
    )


@app.route("/admin/ad-requests/<int:req_id>/approve", methods=["POST"])
@admin_required
def admin_approve_ad_request(req_id):
    req = AdRequest.query.get_or_404(req_id)

    if req.status != "pending":
        flash("Эта заявка уже обработана.", "error")
        return redirect(url_for("admin_ad_requests"))

    ad = Ad(
        title=req.title,
        text=req.text,
        author_name=req.user.username,
        pavilion_id=req.pavilion_id
    )
    db.session.add(ad)

    req.status = "approved"
    db.session.commit()

    flash("Объявление опубликовано в павильоне.", "success")
    return redirect(url_for("pavilion_page", pavilion_id=req.pavilion_id))


@app.route("/admin/ad-requests/<int:req_id>/reject", methods=["POST"])
@admin_required
def admin_reject_ad_request(req_id):
    req = AdRequest.query.get_or_404(req_id)

    if req.status != "pending":
        flash("Эта заявка уже обработана.", "error")
    else:
        req.status = "rejected"
        db.session.commit()
        flash("Заявка на объявление отклонена.", "info")

    return redirect(url_for("admin_ad_requests"))


@app.route("/admin/support/reply/<int:msg_id>", methods=["POST"])
@admin_required
def admin_support_reply(msg_id):
    msg = SupportMessage.query.get_or_404(msg_id)
    reply_text = request.form.get("reply_text", "").strip()

    if not reply_text:
        flash("Нельзя отправить пустой ответ.", "error")
        return redirect(url_for("admin_support"))

    msg.admin_reply = reply_text
    msg.replied_at = datetime.utcnow()
    msg.status = "done"          # помечаем как обработанное
    db.session.commit()

    flash("Ответ отправлен и сохранён в обращении.", "success")
    return redirect(url_for("admin_support"))

@app.route("/ad/<int:ad_id>/chat", methods=["GET", "POST"])
def ad_chat(ad_id):
    # 1. Проверяем, что пользователь авторизован
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # 2. Получаем объявление
    ad = Ad.query.get_or_404(ad_id)

    # 3. Берём мастера из БД.
    # Если у объявления мастера пока нет (NULL) — временно считаем, что это Кирилл (id=4),
    # но уже ЧЕРЕЗ БД: в таблице у всех стоит 4.
    master_id = ad.master_id or 4

    # 4. Обработка отправки сообщения
    if request.method == "POST":
        text = request.form.get("message", "").strip()
        if text:
            # Если пишет обычный пользователь — сообщение идёт мастеру
            if user_id != master_id:
                receiver_id = master_id
            else:
                # Если пишет мастер — пытаемся ответить последнему "другому" собеседнику
                last_other = (
                    AdMessage.query
                    .filter(
                        AdMessage.ad_id == ad.id,
                        AdMessage.sender_id != master_id
                    )
                    .order_by(AdMessage.created_at.desc())
                    .first()
                )
                receiver_id = last_other.sender_id if last_other else master_id

            msg = AdMessage(
                ad_id=ad.id,
                sender_id=user_id,
                receiver_id=receiver_id,
                text=text,
            )
            db.session.add(msg)
            db.session.commit()

        return redirect(url_for("ad_chat", ad_id=ad.id))

    # 5. Достаём сообщения по этому объявлению
    messages = (
        AdMessage.query
        .filter_by(ad_id=ad.id)
        .order_by(AdMessage.created_at)
        .all()
    )

    # 6. Карта id → имя пользователя, чтобы красиво подписывать отправителей
    users_map = {}
    if messages:
        ids = {m.sender_id for m in messages} | {m.receiver_id for m in messages}
        users = User.query.filter(User.id.in_(ids)).all()
        users_map = {u.id: u.username for u in users}

    return render_template(
        "ad_chat.html",
        ad=ad,
        messages=messages,
        users_map=users_map,
        current_user_id=user_id,
        master_id=master_id,
    )


# --- страница "Сообщения" для мастера ---
# --- страница "Сообщения" для мастера ---
@app.route("/ad/messages")
def ad_messages():
    # неавторизованных отправляем на логин
    if "user_id" not in session:
        return redirect(url_for("login"))

    # доступ только для роли master
    if session.get("user_role") != "master":
        return redirect(url_for("index"))

    master_id = session["user_id"]

    # все объявления этого мастера (важно: у модели Ad есть поле master_id)
    ads = Ad.query.filter_by(master_id=master_id).all()

    return render_template("ad_messages.html", ads=ads)




if __name__ == "__main__":
    app.run(debug=True)
