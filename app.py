from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

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
    code = db.Column(db.String(50), nullable=False, unique=True)  # it / design / study / photo


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

    pavilion_id = db.Column(db.Integer, db.ForeignKey('pavilions.id'), nullable=False)
    pavilion = db.relationship('Pavilion', backref='ads')


# ---------- СОЗДАНИЕ ТАБЛИЦ ----------

with app.app_context():
    db.create_all()


# ---------- МАРШРУТЫ ----------

def get_student_info():
    # чтобы не дублировать строки
    return "Филатова Виктория", "ФБИ-34"


@app.route("/")
def index():
    streets = Street.query.all()
    # до 12 объявлений для витрины
    featured_ads = Ad.query.limit(12).all()

    fio = "Филатова Виктория"
    group = "ФБИ-34"

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


if __name__ == "__main__":
    app.run(debug=True)
