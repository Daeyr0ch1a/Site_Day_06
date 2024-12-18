from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
import os
from models import db, User, Photo
from sqlalchemy.orm import Session

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/uploads')
db.init_app(app)

# Инициализация миграции
migrate = Migrate(app, db)

# Настройка Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # Указываем путь для аутентификации

@login_manager.user_loader
def load_user(user_id):
    with Session(db.engine) as session:
        return session.get(User, int(user_id))

# Главная страница
@app.route("/")
def home():
    photos = Photo.query.all()  # Все фото
    return render_template("home.html", photos=photos, title="Главная - PleinAir.Art")

# Страница избранных фото
@app.route("/favorites")
@login_required
def favorites():
    photos = Photo.query.filter_by(user_id=current_user.id, is_favorite=True).all()
    return render_template("favorites.html", photos=photos, title="Избранное - PleinAir.Art")

@app.route("/photo/<int:photo_id>")
def view_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    return render_template("view_photo.html", photo=photo, title=f"Фото {photo_id} - PleinAir.Art")

# Удаление фото
@app.route("/photo/<int:photo_id>/delete", methods=["POST"])
@login_required
def delete_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    if photo.user_id != current_user.id:
        return "Вы не можете удалить это фото.", 403

    db.session.delete(photo)
    db.session.commit()
    flash("Фото успешно удалено!")
    return redirect(url_for("gallery"))

# Редактирование фото
@app.route("/photo/<int:photo_id>/edit", methods=["GET", "POST"])
@login_required
def edit_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    if photo.user_id != current_user.id:
        return "Вы не можете редактировать это фото.", 403

    if request.method == "POST":
        photo.title = request.form.get("title")
        photo.description = request.form.get("description")
        db.session.commit()
        flash("Фото успешно отредактировано!")
        return redirect(url_for("gallery"))

    return render_template("edit_photo.html", photo=photo, title=f"Редактирование {photo.title} - PleinAir.Art")

# Галерея пользователя
@app.route("/gallery")
@login_required
def gallery():
    photos = Photo.query.filter_by(user_id=current_user.id).all()
    return render_template("gallery.html", photos=photos, title="Моя галерея - PleinAir.Art")

# Добавление/удаление фото в избранное
@app.route("/photo/<int:photo_id>/favorite", methods=["POST"])
@login_required
def favorite_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    if photo.user_id != current_user.id:
        return "Вы не можете редактировать это фото.", 403

    photo.is_favorite = not photo.is_favorite  # Переключаем статус избранного
    db.session.commit()
    flash("Статус избранного обновлен!")
    return redirect(url_for("gallery"))

# Страница входа
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Поиск пользователя
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            login_user(user)
            flash("Вы успешно вошли!")
            return redirect(url_for("home"))
        else:
            flash("Неверные учетные данные. Попробуйте снова.")
    return render_template("login.html", title="Вход - PleinAir.Art")

# Страница регистрации
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        # Проверка уникальности пользователя
        if User.query.filter_by(username=username).first():
            flash("Пользователь с таким именем уже существует.")
            return redirect(url_for("register"))

        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        flash("Регистрация успешна!")
        return redirect(url_for("home"))
    return render_template("register.html", title="Регистрация - PleinAir.Art")

# Выход
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Вы вышли из системы!")
    return redirect(url_for("home"))

# Загрузка фото
@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        if 'photo' not in request.files:
            flash('Файл не выбран.')
            return redirect(request.url)

        file = request.files['photo']
        title = request.form.get("title")
        description = request.form.get("description")

        if file.filename == '':
            flash('Файл не выбран.')
            return redirect(request.url)

        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            new_photo = Photo(filename=filename, title=title, description=description, user_id=current_user.id)
            db.session.add(new_photo)
            db.session.commit()
            flash("Фото успешно загружено!")
            return redirect(url_for("gallery"))

    return render_template("upload.html", title="Загрузка фото - PleinAir.Art")

# Создание базы данных
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
