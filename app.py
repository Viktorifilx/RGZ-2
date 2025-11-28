from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash, make_response
)
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from functools import wraps
import os
from sqlalchemy import or_, inspect, text

app = Flask(__name__)

# ключ сессии
app.secret_key = "super_secret_key_change_me"

# === загрузка аватаров ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads", "avatars")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# путь к БД
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "fair.db")
DB_URI = "sqlite:///" + DB_PATH.replace("\\", "/")

app.config["SQLALCHEMY_DATABASE_URI"] = DB_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ===== МОДЕЛИ =====


class Street(db.Model):
    __tablename__ = "streets"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(50), nullable=False, unique=True)

    # улица → павильоны
    pavilions = db.relationship("Pavilion", backref="street", lazy="select")


class Pavilion(db.Model):
    __tablename__ = "pavilions"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    street_id = db.Column(db.Integer, db.ForeignKey("streets.id"), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # павильон → объявления
    ads = db.relationship("Ad", backref="pavilion", lazy="select")


class Ad(db.Model):
    __tablename__ = "ads"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    text = db.Column(db.Text, nullable=False)

    # запасное имя
    author_name = db.Column(db.String(120))

    pavilion_id = db.Column(
        db.Integer,
        db.ForeignKey("pavilions.id"),
        nullable=False,
    )

    # мастер из users
    master_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True,
    )

    master = db.relationship("User", foreign_keys=[master_id])

    @property
    def master_display_name(self):
        if self.master and self.master.username:
            return self.master.username
        if self.author_name:
            return self.author_name
        return "Мастер"


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), nullable=False)  # логин
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # хеш пароля
    role = db.Column(db.String(20), nullable=False, default="user")

    # НОВОЕ: имя и файл аватарки
    full_name = db.Column(db.String(120), nullable=True)  # настоящее имя
    avatar_filename = db.Column(db.String(255), nullable=True)  # имя файла в /static/uploads/avatars


class StreetRequest(db.Model):
    __tablename__ = "street_requests"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("User", backref="street_requests")

    street_name = db.Column(db.String(120), nullable=False)
    street_code = db.Column(db.String(50), nullable=False)
    pavilion_title = db.Column(db.String(150), nullable=False)
    pavilion_desc = db.Column(db.Text, nullable=True)

    status = db.Column(db.String(20), nullable=False, default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    street_id = db.Column(db.Integer, db.ForeignKey("streets.id"), nullable=True)


class AdRequest(db.Model):
    __tablename__ = "ad_requests"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("User", backref="ad_requests")

    pavilion_id = db.Column(db.Integer, db.ForeignKey("pavilions.id"), nullable=False)
    pavilion = db.relationship("Pavilion", backref="ad_requests")

    title = db.Column(db.String(250), nullable=False)
    text = db.Column(db.Text, nullable=False)

    status = db.Column(db.String(20), nullable=False, default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SupportMessage(db.Model):
    __tablename__ = "support_messages"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("User", backref="support_messages")

    subject = db.Column(db.String(200), nullable=False)
    text = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="new")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    admin_reply = db.Column(db.Text, nullable=True)
    replied_at = db.Column(db.DateTime, nullable=True)


class AdMessage(db.Model):
    __tablename__ = "ad_messages"

    id = db.Column(db.Integer, primary_key=True)
    ad_id = db.Column(db.Integer, db.ForeignKey("ads.id"), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    is_read = db.Column(db.Boolean, default=False, nullable=False)


class PavilionRequest(db.Model):
    __tablename__ = "pavilion_requests"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("User", backref="pavilion_requests")

    street_id = db.Column(db.Integer, db.ForeignKey("streets.id"), nullable=False)
    street = db.relationship("Street", backref="pavilion_requests")

    # старое поле title
    title = db.Column(db.String(200), nullable=False, default="")

    pavilion_title = db.Column(db.String(150), nullable=True)
    pavilion_desc = db.Column(db.Text, nullable=True)

    ad_title = db.Column(db.String(250), nullable=True)
    ad_text = db.Column(db.Text, nullable=True)

    status = db.Column(db.String(20), nullable=False, default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ===== СОЗДАНИЕ ТАБЛИЦ И МИГРАЦИЯ =====

with app.app_context():
    db.create_all()

with app.app_context():
    insp = inspect(db.engine)
    if "pavilion_requests" in insp.get_table_names():
        cols = [c["name"] for c in insp.get_columns("pavilion_requests")]

        if "pavilion_title" not in cols:
            db.session.execute(
                text(
                    "ALTER TABLE pavilion_requests "
                    "ADD COLUMN pavilion_title VARCHAR(150)"
                )
            )

        if "pavilion_desc" not in cols:
            db.session.execute(
                text(
                    "ALTER TABLE pavilion_requests "
                    "ADD COLUMN pavilion_desc TEXT"
                )
            )

        if "ad_title" not in cols:
            db.session.execute(
                text(
                    "ALTER TABLE pavilion_requests "
                    "ADD COLUMN ad_title VARCHAR(250)"
                )
            )

        if "ad_text" not in cols:
            db.session.execute(
                text(
                    "ALTER TABLE pavilion_requests "
                    "ADD COLUMN ad_text TEXT"
                )
            )

        db.session.commit()


# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====


def get_student_info():
    return "Филатова Виктория", "ФБИ-34"


def recalc_unread_total():
    """Счётчик непрочитанных сообщений по объявлениям."""
    if "user_id" not in session:
        session["unread_total"] = 0
        return

    user_id = session["user_id"]
    role = session.get("user_role")

    # мастер
    if role == "master":
        ads = Ad.query.filter_by(master_id=user_id).all()
        if not ads:
            session["unread_total"] = 0
            return

        ad_ids = [a.id for a in ads]

        unread_total = AdMessage.query.filter(
            AdMessage.ad_id.in_(ad_ids),
            AdMessage.receiver_id == user_id,
            AdMessage.is_read.is_(False),
        ).count()
        session["unread_total"] = unread_total
        return

    # обычный пользователь
    unread_total = AdMessage.query.filter_by(
        receiver_id=user_id,
        is_read=False,
    ).count()
    session["unread_total"] = unread_total


def recalc_support_badge():
    """Счётчики по поддержке."""
    if "user_id" not in session:
        session["support_unread"] = 0
        session["admin_support_new"] = 0
        return

    role = session.get("user_role")

    # админ
    if role == "admin":
        session["support_unread"] = 0
        session["admin_support_new"] = SupportMessage.query.filter_by(
            status="new"
        ).count()
        return

    # пользователь / мастер
    user_id = session["user_id"]

    last_seen_str = session.get("support_seen_at")
    last_seen = None
    if last_seen_str:
        try:
            last_seen = datetime.fromisoformat(last_seen_str)
        except ValueError:
            last_seen = None

    q = SupportMessage.query.filter_by(user_id=user_id)
    q = q.filter(SupportMessage.admin_reply.isnot(None))
    q = q.filter(SupportMessage.replied_at.isnot(None))

    if last_seen is not None:
        q = q.filter(SupportMessage.replied_at > last_seen)

    session["support_unread"] = q.count()


def recalc_admin_counters():
    """Счётчики для админа."""
    if session.get("user_role") != "admin":
        session["admin_requests"] = 0
        session["admin_support_new"] = 0
        return

    pending_ads = AdRequest.query.filter_by(status="pending").count()
    pending_pav = PavilionRequest.query.filter_by(status="pending").count()
    pending_streets = StreetRequest.query.filter_by(status="pending").count()

    session["admin_requests"] = pending_ads + pending_pav + pending_streets
    session["admin_support_new"] = SupportMessage.query.filter_by(
        status="new"
    ).count()


@app.before_request
def auto_update_unread():
    """Обновление счётчиков перед каждым запросом."""
    if "user_id" in session:
        # 🔄 каждый запрос подтягиваем актуальные данные пользователя из БД
        user = User.query.get(session["user_id"])
        if user:
            session["avatar_filename"] = user.avatar_filename
            session["full_name"] = user.full_name

        recalc_unread_total()
        recalc_support_badge()
        recalc_admin_counters()
    else:
        session["unread_total"] = 0
        session["support_unread"] = 0
        session["admin_support_new"] = 0
        session["admin_requests"] = 0



def login_required(view_func):
    """Защита входом."""

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Нужно войти на сайт.", "error")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapped


def admin_required(view_func):
    """Только админ."""

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if session.get("user_role") != "admin":
            flash("Доступ только для администратора.", "error")
            return redirect(url_for("index"))
        return view_func(*args, **kwargs)

    return wrapped


# ===== ПОЛЬЗОВАТЕЛЬСКИЕ СТРАНИЦЫ =====


@app.route("/")
def index():
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
        group=group,
    )


@app.route("/street/<code>")
def street_page(code):
    street = Street.query.filter_by(code=code).first_or_404()
    pavilions = Pavilion.query.filter_by(street_id=street.id).order_by(
        Pavilion.id
    ).all()

    fio, group = get_student_info()
    return render_template(
        "street.html",
        street=street,
        pavilions=pavilions,
        fio=fio,
        group=group,
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
        group=group,
    )


# ===== ЗАЯВКА НА ОБЪЯВЛЕНИЕ В ПАВИЛЬОН =====


@app.route("/pavilion/<int:pavilion_id>/offer", methods=["GET", "POST"])
@login_required
def offer_ad(pavilion_id):
    fio, group = get_student_info()
    pavilion = Pavilion.query.get_or_404(pavilion_id)

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
                status="pending",
            )
            db.session.add(req)
            db.session.commit()

            recalc_admin_counters()
            flash("Заявка на объявление отправлена администратору.", "success")
            return redirect(url_for("pavilion_page", pavilion_id=pavilion.id))

    return render_template(
        "offer_ad.html",
        pavilion=pavilion,
        form=form,
        errors=errors,
        fio=fio,
        group=group,
    )


@app.route("/ad/<int:ad_id>")
def ad_page(ad_id):
    ad = Ad.query.get_or_404(ad_id)
    fio, group = get_student_info()
    return render_template("ad.html", ad=ad, fio=fio, group=group)


# ===== РЕГИСТРАЦИЯ / ВХОД =====


@app.route("/register", methods=["GET", "POST"])
def register():
    errors = []

    if request.method == "POST":
        username = request.form.get("username", "").strip()  # логин
        full_name = request.form.get("full_name", "").strip()  # имя
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "user")

        # файл аватарки
        avatar_file = request.files.get("avatar")
        avatar_filename = None

        # простая валидация
        if not username:
            errors.append("Введите логин.")
        if not email:
            errors.append("Введите e-mail.")
        if not password:
            errors.append("Введите пароль.")
        if User.query.filter_by(email=email).first():
            errors.append("Пользователь с таким e-mail уже существует.")
        if User.query.filter_by(username=username).first():
            errors.append("Пользователь с таким логином уже существует.")

        # если всё ок, сохраняем аватар
        if not errors and avatar_file and avatar_file.filename:
            if allowed_file(avatar_file.filename):
                from werkzeug.utils import secure_filename
                from time import time

                safe_name = secure_filename(avatar_file.filename)
                ext = safe_name.rsplit(".", 1)[1].lower()
                avatar_filename = f"{int(time())}_{username}.{ext}"
                avatar_path = os.path.join(app.config["UPLOAD_FOLDER"], avatar_filename)
                avatar_file.save(avatar_path)
            else:
                errors.append(
                    "Аватарку нужно загрузить в формате: png, jpg, jpeg, gif, webp."
                )

        if not errors:
            user = User(
                username=username,
                full_name=full_name or None,
                email=email,
                password=generate_password_hash(password),
                role=role,
                avatar_filename=avatar_filename,
            )
            db.session.add(user)
            db.session.commit()

            flash("Аккаунт успешно создан. Теперь можно войти.", "success")
            return redirect(url_for("login"))

    return render_template("register.html", errors=errors)


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
            ok = False
            try:
                if check_password_hash(user.password, password):
                    ok = True
            except ValueError:
                if user.password == password:
                    ok = True

            if not ok:
                errors.append("Неверный пароль.")

            if not errors and user:
                session["user_id"] = user.id
                session["username"] = user.username
                session["user_role"] = user.role
                session["avatar_filename"] = user.avatar_filename
                session["full_name"] = user.full_name

                recalc_unread_total()
                recalc_support_badge()
                return redirect(url_for("index"))

    return render_template("login.html", errors=errors)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/account/delete", methods=["GET", "POST"])
@login_required
def delete_account():
    user_id = session["user_id"]
    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        # 1. удаляем все сообщения по объявлениям
        AdMessage.query.filter(
            (AdMessage.sender_id == user_id) | (AdMessage.receiver_id == user_id)
        ).delete(synchronize_session=False)

        # 2. обращения в поддержку
        SupportMessage.query.filter_by(user_id=user_id).delete(
            synchronize_session=False
        )

        # 3. заявки пользователя
        StreetRequest.query.filter_by(user_id=user_id).delete(
            synchronize_session=False
        )
        AdRequest.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        PavilionRequest.query.filter_by(user_id=user_id).delete(
            synchronize_session=False
        )

        # 4. если это мастер – удаляем все его объявления
        if user.role == "master":
            Ad.query.filter_by(master_id=user_id).delete(synchronize_session=False)

        # 5. сам пользователь
        db.session.delete(user)
        db.session.commit()

        session.clear()
        flash("Аккаунт удалён.", "success")
        return redirect(url_for("index"))

    fio, group = get_student_info()
    return render_template("account_delete.html", fio=fio, group=group)


# ===== ПРОСТЫЕ СТРАНИЦЫ =====


@app.route("/how-it-works")
def how_it_works():
    fio, group = get_student_info()
    return render_template("how_it_works.html", fio=fio, group=group)


@app.route("/about")
def about():
    fio, group = get_student_info()
    return render_template("about.html", fio=fio, group=group)


# ===== ЗАЯВКА НА НОВУЮ УЛИЦУ =====


@app.route("/street/request", methods=["GET", "POST"])
@login_required
def request_street():
    fio, group = get_student_info()

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
            errors.append("Укажите код улицы латиницей.")
        else:
            cleaned = form["street_code"].replace("_", "")
            if not cleaned.isalnum() or not form["street_code"].islower():
                errors.append(
                    "Код только строчными латинскими буквами, цифрами и подчёркиваниями."
                )
            else:
                exists = Street.query.filter_by(code=form["street_code"]).first()
                if exists:
                    errors.append("Такой код улицы уже занят.")

        if not form["pavilion_title"]:
            errors.append("Введите название первого павильона.")

        if not errors:
            req = StreetRequest(
                user_id=session["user_id"],
                street_name=form["street_name"],
                street_code=form["street_code"],
                pavilion_title=form["pavilion_title"],
                pavilion_desc=form["pavilion_desc"],
                status="pending",
            )
            db.session.add(req)
            db.session.commit()

            recalc_admin_counters()
            flash("Заявка на улицу отправлена администратору.", "success")
            return redirect(url_for("index"))

    return render_template(
        "street_request.html",
        fio=fio,
        group=group,
        form=form,
        errors=errors,
    )


# ===== ПОДДЕРЖКА =====


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
                status="new",
            )
            db.session.add(msg)
            db.session.commit()

            recalc_admin_counters()
            flash("Сообщение отправлено администратору.", "success")
            return redirect(url_for("support"))

    my_messages = (
        SupportMessage.query.filter_by(user_id=session["user_id"])
        .order_by(SupportMessage.created_at.desc())
        .limit(10)
        .all()
    )

    session["support_seen_at"] = datetime.utcnow().isoformat()
    recalc_support_badge()

    return render_template(
        "support.html",
        fio=fio,
        group=group,
        errors=errors,
        my_messages=my_messages,
    )


# ===== АДМИН: ГЛАВНАЯ =====


@app.route("/admin")
@admin_required
def admin_dashboard():
    fio, group = get_student_info()
    streets = Street.query.order_by(Street.id).all()
    return render_template(
        "admin_dashboard.html",
        fio=fio,
        group=group,
        streets=streets,
    )


# ===== АДМИН: ЗАЯВКИ НА УЛИЦЫ =====


@app.route("/admin/requests")
@admin_required
def admin_requests():
    fio, group = get_student_info()
    requests_list = StreetRequest.query.order_by(
        StreetRequest.created_at.desc()
    ).all()

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
        stats=stats,
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
        street=new_street,
    )
    db.session.add(pav)

    req.status = "approved"
    req.street_id = new_street.id

    db.session.commit()

    recalc_admin_counters()
    flash("Улица и павильон созданы.", "success")
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
        recalc_admin_counters()
        flash("Заявка отклонена.", "info")

    return redirect(url_for("admin_requests"))


# ===== АДМИН: ПОДДЕРЖКА =====


@app.route("/admin/support")
@admin_required
def admin_support():
    fio, group = get_student_info()
    messages = SupportMessage.query.order_by(
        SupportMessage.created_at.desc()
    ).all()

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
        stats=stats,
    )


@app.route("/admin/support/<int:msg_id>/close", methods=["POST"])
@admin_required
def close_support(msg_id):
    msg = SupportMessage.query.get_or_404(msg_id)
    msg.status = "done"
    db.session.commit()

    recalc_admin_counters()
    flash("Обращение помечено как обработанное.", "success")
    return redirect(url_for("admin_support"))


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
    msg.status = "done"
    db.session.commit()

    recalc_admin_counters()
    flash("Ответ отправлен и сохранён.", "success")
    return redirect(url_for("admin_support"))


# ===== АДМИН: ПОЛЬЗОВАТЕЛИ =====


@app.route("/admin/users")
@admin_required
def admin_users():
    """Список всех пользователей для администратора."""
    fio, group = get_student_info()
    users = User.query.order_by(User.id).all()
    return render_template(
        "admin_users.html",
        fio=fio,
        group=group,
        users=users,
    )


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def admin_delete_user(user_id):
    """Удаление учётной записи пользователем-админом."""

    # нельзя удалить себя
    if user_id == session.get("user_id"):
        flash("Нельзя удалить собственный админ-аккаунт.", "error")
        return redirect(url_for("admin_users"))

    user = User.query.get_or_404(user_id)

    # подстрахуемся: не удаляем других админов
    if user.role == "admin":
        flash("Нельзя удалить администраторский аккаунт.", "error")
        return redirect(url_for("admin_users"))

    # 1. сообщения по объявлениям
    AdMessage.query.filter(
        (AdMessage.sender_id == user_id) | (AdMessage.receiver_id == user_id)
    ).delete(synchronize_session=False)

    # 2. обращения в поддержку
    SupportMessage.query.filter_by(user_id=user_id).delete(
        synchronize_session=False
    )

    # 3. заявки
    StreetRequest.query.filter_by(user_id=user_id).delete(
        synchronize_session=False
    )
    AdRequest.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    PavilionRequest.query.filter_by(user_id=user_id).delete(
        synchronize_session=False
    )

    # 4. если это мастер – удаляем все его объявления
    if user.role == "master":
        Ad.query.filter_by(master_id=user_id).delete(synchronize_session=False)

    # 5. сам пользователь
    db.session.delete(user)
    db.session.commit()

    flash("Учётная запись удалена.", "success")
    return redirect(url_for("admin_users"))


# ===== АДМИН: ПАВИЛЬОНЫ И ОБЪЯВЛЕНИЯ =====


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


@app.route("/admin/ad/<int:ad_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_edit_ad(ad_id):
    """Редактирование текста объявления администратором."""
    ad = Ad.query.get_or_404(ad_id)

    fio, group = get_student_info()
    errors = []
    title_val = ad.title
    text_val = ad.text

    if request.method == "POST":
        title_val = request.form.get("title", "").strip()
        text_val = request.form.get("text", "").strip()

        if not title_val:
            errors.append("Введите заголовок объявления.")
        if not text_val:
            errors.append("Введите текст объявления.")

        if not errors:
            ad.title = title_val
            ad.text = text_val
            db.session.commit()
            flash("Объявление сохранено.", "success")
            return redirect(url_for("pavilion_page", pavilion_id=ad.pavilion_id))

    form = {"title": title_val, "text": text_val}
    return render_template(
        "admin_edit_ad.html",
        ad=ad,
        form=form,
        errors=errors,
        fio=fio,
        group=group,
    )


@app.route("/admin/delete-ad/<int:ad_id>", methods=["POST"])
@admin_required
def admin_delete_ad_legacy(ad_id):
    return admin_delete_ad(ad_id)


# ===== ОБЪЯВЛЕНИЯ: МАСТЕР УДАЛЯЕТ/РЕДАКТИРУЕТ СВОИ =====


@app.route("/my/ad/<int:ad_id>/delete", methods=["POST"])
@login_required
def delete_own_ad(ad_id):
    """Удаление объявления самим мастером."""
    ad = Ad.query.get_or_404(ad_id)
    user_id = session.get("user_id")
    role = session.get("user_role")

    # Разрешаем только мастеру и только своё объявление
    if role != "master" or ad.master_id != user_id:
        flash("Вы можете удалять только свои объявления.", "error")
        return redirect(url_for("ad_page", ad_id=ad.id))

    pavilion_id = ad.pavilion_id

    db.session.delete(ad)
    db.session.commit()

    flash("Объявление удалено.", "success")
    return redirect(url_for("pavilion_page", pavilion_id=pavilion_id))


@app.route("/my/ad/<int:ad_id>/edit", methods=["GET", "POST"])
@login_required
def edit_own_ad(ad_id):
    """Редактирование объявления самим мастером."""
    ad = Ad.query.get_or_404(ad_id)
    user_id = session.get("user_id")
    role = session.get("user_role")

    # разрешаем только мастеру-автору
    if role != "master" or ad.master_id != user_id:
        flash("Вы можете редактировать только свои объявления.", "error")
        return redirect(url_for("ad_page", ad_id=ad.id))

    errors = []
    form = {"title": ad.title, "text": ad.text}

    if request.method == "POST":
        form["title"] = request.form.get("title", "").strip()
        form["text"] = request.form.get("text", "").strip()

        if not form["title"]:
            errors.append("Введите заголовок объявления.")
        if not form["text"]:
            errors.append("Опишите, чем вы можете помочь.")

        if not errors:
            ad.title = form["title"]
            ad.text = form["text"]
            db.session.commit()

            flash("Объявление обновлено.", "success")
            return redirect(url_for("ad_page", ad_id=ad.id))

    fio, group = get_student_info()
    return render_template(
        "edit_ad.html",
        ad=ad,
        form=form,
        errors=errors,
        fio=fio,
        group=group,
    )


# ===== СООБЩЕНИЯ МАСТЕРА ПО ОБЪЯВЛЕНИЯМ =====


@app.route("/ad/messages")
def ad_messages():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    if session.get("user_role") != "master":
        flash("Страница сообщений доступна только мастеру.", "error")
        return redirect(url_for("index"))

    fio, group = get_student_info()

    ads = Ad.query.filter_by(master_id=user_id).all()
    if not ads:
        recalc_unread_total()
        html = render_template("ad_messages.html", items=[], fio=fio, group=group)
        resp = make_response(html)
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp

    ad_ids = [a.id for a in ads]
    ad_map = {a.id: a for a in ads}

    all_msgs = (
        AdMessage.query.filter(AdMessage.ad_id.in_(ad_ids))
        .order_by(AdMessage.created_at)
        .all()
    )

    threads = {}
    client_ids = set()

    for m in all_msgs:
        if m.sender_id == user_id and m.receiver_id != user_id:
            client_id = m.receiver_id
        elif m.receiver_id == user_id and m.sender_id != user_id:
            client_id = m.sender_id
        else:
            continue

        key = (m.ad_id, client_id)
        if key not in threads:
            threads[key] = {
                "ad": ad_map.get(m.ad_id),
                "client_id": client_id,
                "unread_count": 0,
                "last_time": m.created_at,
            }
        else:
            if (
                m.created_at
                and threads[key]["last_time"]
                and m.created_at > threads[key]["last_time"]
            ):
                threads[key]["last_time"] = m.created_at

        if m.receiver_id == user_id and not m.is_read:
            threads[key]["unread_count"] += 1

        client_ids.add(client_id)

    users = User.query.filter(User.id.in_(client_ids)).all() if client_ids else []
    user_map = {u.id: u.username for u in users}

    items = []
    total_unread = 0
    for (ad_id, client_id), data in threads.items():
        data["client_name"] = user_map.get(client_id, f"ID {client_id}")
        items.append(data)
        total_unread += data["unread_count"]

    items.sort(
        key=lambda x: x["last_time"] or datetime.min,
        reverse=True,
    )

    session["unread_total"] = total_unread

    html = render_template("ad_messages.html", items=items, fio=fio, group=group)
    resp = make_response(html)
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@app.route("/ad/<int:ad_id>/chat", methods=["GET", "POST"])
def ad_chat(ad_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    ad = Ad.query.get_or_404(ad_id)
    master_id = ad.master_id

    if master_id is None:
        flash("У этого объявления ещё не назначен мастер.", "error")
        return redirect(url_for("ad_page", ad_id=ad.id))

    # пользователь
    if user_id != master_id:
        if request.method == "POST":
            text = request.form.get("message", "").strip()
            if text:
                msg = AdMessage(
                    ad_id=ad.id,
                    sender_id=user_id,
                    receiver_id=master_id,
                    text=text,
                    is_read=False,
                )
                db.session.add(msg)
                db.session.commit()
                recalc_unread_total()

            return redirect(url_for("ad_chat", ad_id=ad.id))

        AdMessage.query.filter_by(
            ad_id=ad.id, receiver_id=user_id, is_read=False
        ).update({"is_read": True}, synchronize_session=False)
        db.session.commit()
        recalc_unread_total()

        messages = (
            AdMessage.query.filter(
                AdMessage.ad_id == ad.id,
                or_(
                    AdMessage.sender_id == user_id,
                    AdMessage.receiver_id == user_id,
                ),
            )
            .order_by(AdMessage.created_at)
            .all()
        )

        if not messages:
            messages = (
                AdMessage.query.filter_by(ad_id=ad.id)
                .order_by(AdMessage.created_at)
                .all()
            )

        user_ids = {m.sender_id for m in messages} | {m.receiver_id for m in messages}
        users = User.query.filter(User.id.in_(user_ids)).all() if user_ids else []
        users_map = {u.id: u.username for u in users}

        fio, group = get_student_info()

        return render_template(
            "ad_chat.html",
            ad=ad,
            messages=messages,
            users_map=users_map,
            current_user_id=user_id,
            master_id=master_id,
            fio=fio,
            group=group,
        )

    # мастер
    client_id = request.args.get("client_id", type=int)

    if not client_id:
        last_msg = (
            AdMessage.query.filter_by(ad_id=ad.id)
            .order_by(AdMessage.created_at.desc())
            .first()
        )
        if last_msg:
            if last_msg.sender_id != master_id:
                client_id = last_msg.sender_id
            elif last_msg.receiver_id != master_id:
                client_id = last_msg.receiver_id

    if not client_id:
        fio, group = get_student_info()
        flash("Пока нет сообщений по этому объявлению.", "info")
        return render_template(
            "ad_chat.html",
            ad=ad,
            messages=[],
            users_map={},
            current_user_id=user_id,
            master_id=master_id,
            fio=fio,
            group=group,
        )

    participants = {master_id, client_id}

    if request.method == "POST":
        text = request.form.get("message", "").strip()
        if text:
            msg = AdMessage(
                ad_id=ad.id,
                sender_id=user_id,
                receiver_id=client_id,
                text=text,
                is_read=False,
            )
            db.session.add(msg)
            db.session.commit()
            recalc_unread_total()

        return redirect(url_for("ad_chat", ad_id=ad.id, client_id=client_id))

    AdMessage.query.filter(
        AdMessage.ad_id == ad.id,
        AdMessage.receiver_id == user_id,
        AdMessage.sender_id == client_id,
        AdMessage.is_read.is_(False),
    ).update({"is_read": True}, synchronize_session=False)
    db.session.commit()
    recalc_unread_total()

    messages = (
        AdMessage.query.filter(
            AdMessage.ad_id == ad.id,
            AdMessage.sender_id.in_(participants),
            AdMessage.receiver_id.in_(participants),
        )
        .order_by(AdMessage.created_at)
        .all()
    )

    user_ids = {m.sender_id for m in messages} | {m.receiver_id for m in messages}
    users = User.query.filter(User.id.in_(user_ids)).all() if user_ids else []
    users_map = {u.id: u.username for u in users}

    fio, group = get_student_info()

    return render_template(
        "ad_chat.html",
        ad=ad,
        messages=messages,
        users_map=users_map,
        current_user_id=user_id,
        master_id=master_id,
        fio=fio,
        group=group,
    )


# ===== СООБЩЕНИЯ ПОЛЬЗОВАТЕЛЯ =====


@app.route("/my/messages")
def user_messages():
    """Диалоги пользователя с мастерами."""
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    if session.get("user_role") != "user":
        flash("Страница сообщений только для пользователей.", "error")
        return redirect(url_for("index"))

    fio, group = get_student_info()

    all_msgs = (
        AdMessage.query.filter(
            (AdMessage.sender_id == user_id) | (AdMessage.receiver_id == user_id)
        )
        .order_by(AdMessage.created_at)
        .all()
    )

    if not all_msgs:
        items = []
    else:
        threads = {}
        ad_ids = set()

        for m in all_msgs:
            ad_ids.add(m.ad_id)

        ads = Ad.query.filter(Ad.id.in_(ad_ids)).all()
        ad_map = {a.id: a for a in ads}

        for m in all_msgs:
            ad = ad_map.get(m.ad_id)
            if not ad or not ad.master_id:
                continue

            master_id = ad.master_id
            key = (m.ad_id, master_id)

            if key not in threads:
                threads[key] = {
                    "ad": ad,
                    "master_id": master_id,
                    "unread_count": 0,
                    "last_time": m.created_at,
                }
            else:
                if (
                    m.created_at
                    and threads[key]["last_time"]
                    and m.created_at > threads[key]["last_time"]
                ):
                    threads[key]["last_time"] = m.created_at

            if m.receiver_id == user_id and not m.is_read:
                threads[key]["unread_count"] += 1

        master_ids = {data["master_id"] for data in threads.values()}
        users = User.query.filter(User.id.in_(master_ids)).all() if master_ids else []
        master_map = {u.id: u.username for u in users}

        items = []
        for (ad_id, master_id), data in threads.items():
            data["master_name"] = master_map.get(master_id, f"ID {master_id}")
            items.append(data)

        items.sort(
            key=lambda x: x["last_time"] or datetime.min,
            reverse=True,
        )

    return render_template("user_messages.html", items=items, fio=fio, group=group)


# ===== ЗАЯВКА НА НОВЫЙ ПАВИЛЬОН =====


@app.route("/street/<int:street_id>/pavilion-request", methods=["GET", "POST"])
@login_required
def pavilion_request(street_id):
    """Заявка на новый павильон и первое объявление."""
    street = Street.query.get_or_404(street_id)

    if session.get("user_role") not in ("master", "admin"):
        flash("Предлагать новые павильоны могут только мастера.", "error")
        return redirect(url_for("street_page", code=street.code))

    fio, group = get_student_info()
    errors = []

    form = {
        "pavilion_title": "",
        "pavilion_desc": "",
        "ad_title": "",
        "ad_text": "",
    }

    if request.method == "POST":
        form["pavilion_title"] = request.form.get("pavilion_title", "").strip()
        form["pavilion_desc"] = request.form.get("pavilion_desc", "").strip()
        form["ad_title"] = request.form.get("ad_title", "").strip()
        form["ad_text"] = request.form.get("ad_text", "").strip()

        if not form["pavilion_title"]:
            errors.append("Введите название павильона.")
        if not form["ad_title"]:
            errors.append("Введите заголовок первого объявления.")
        if not form["ad_text"]:
            errors.append("Опишите первое объявление для павильона.")

        if not errors:
            req = PavilionRequest(
                user_id=session["user_id"],
                street_id=street.id,
                title=form["pavilion_title"],
                pavilion_title=form["pavilion_title"],
                pavilion_desc=form["pavilion_desc"],
                ad_title=form["ad_title"],
                ad_text=form["ad_text"],
                status="pending",
            )
            db.session.add(req)
            db.session.commit()

            recalc_admin_counters()
            flash(
                "Заявка на павильон и первое объявление отправлена администратору.",
                "success",
            )
            return redirect(url_for("street_page", code=street.code))

    return render_template(
        "pavilion_request.html",
        street=street,
        form=form,
        errors=errors,
        fio=fio,
        group=group,
    )


@app.route("/admin/pavilion-requests/<int:req_id>/approve", methods=["POST"])
@admin_required
def admin_approve_pavilion_request(req_id):
    req = PavilionRequest.query.get_or_404(req_id)

    if req.status != "pending":
        flash("Эта заявка уже обработана.", "error")
        return redirect(url_for("admin_ad_requests"))

    pav = Pavilion(
        title=req.pavilion_title,
        description=req.pavilion_desc,
        street_id=req.street_id,
    )
    db.session.add(pav)
    db.session.flush()

    ad = Ad(
        title=req.ad_title,
        text=req.ad_text,
        author_name=req.user.username,
        pavilion_id=pav.id,
        master_id=req.user_id,
    )
    db.session.add(ad)

    req.status = "approved"
    db.session.commit()

    recalc_admin_counters()
    flash("Павильон создан, объявление опубликовано.", "success")
    return redirect(url_for("pavilion_page", pavilion_id=pav.id))


@app.route("/admin/pavilion-requests/<int:req_id>/reject", methods=["POST"])
@admin_required
def admin_reject_pavilion_request(req_id):
    req = PavilionRequest.query.get_or_404(req_id)

    if req.status != "pending":
        flash("Эта заявка уже обработана.", "error")
    else:
        req.status = "rejected"
        db.session.commit()
        recalc_admin_counters()
        flash("Заявка на павильон отклонена.", "info")

    return redirect(url_for("admin_ad_requests"))


# ===== АДМИН: ЗАЯВКИ НА ОБЪЯВЛЕНИЯ И ПАВИЛЬОНЫ =====


@app.route("/admin/ad-requests")
@admin_required
def admin_ad_requests():
    fio, group = get_student_info()

    ad_requests = AdRequest.query.order_by(AdRequest.created_at.desc()).all()
    pav_requests = PavilionRequest.query.order_by(
        PavilionRequest.created_at.desc()
    ).all()

    stats_ads = {
        "total": len(ad_requests),
        "pending": sum(1 for r in ad_requests if r.status == "pending"),
        "approved": sum(1 for r in ad_requests if r.status == "approved"),
        "rejected": sum(1 for r in ad_requests if r.status == "rejected"),
    }

    stats_pav = {
        "total": len(pav_requests),
        "pending": sum(1 for r in pav_requests if r.status == "pending"),
        "approved": sum(1 for r in pav_requests if r.status == "approved"),
        "rejected": sum(1 for r in pav_requests if r.status == "rejected"),
    }

    return render_template(
        "admin_ad_requests.html",
        fio=fio,
        group=group,
        ad_requests=ad_requests,
        pav_requests=pav_requests,
        stats_ads=stats_ads,
        stats_pav=stats_pav,
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
        pavilion_id=req.pavilion_id,
        master_id=req.user_id,
    )
    db.session.add(ad)

    req.status = "approved"
    db.session.commit()

    recalc_admin_counters()
    flash("Объявление опубликовано.", "success")
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
        recalc_admin_counters()
        flash("Заявка на объявление отклонена.", "info")

    return redirect(url_for("admin_ad_requests"))


# ===== ЗАПУСК =====

if __name__ == "__main__":
    app.run(debug=True)
