from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

# Инициализация Flask приложения
app = Flask(__name__)
# Секретный ключ для сессий и шифрования
app.secret_key = 'your-secret-key'  # В продакшене используйте надежный случайный ключ
# Конфигурация базы данных SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///twitter_clone.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Создаем папку для базы данных, если её нет
if not os.path.exists('instance'):
    os.makedirs('instance')

db = SQLAlchemy(app)
app.static_folder = 'static'

# Таблица подписок (followers)
followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)

# Определение модел�� пользователя для базы данных
class User(db.Model):
    """
    Модель пользователя с полями:
    - id: уникальный идентификатор
    - username: уникальное имя пользователя
    - email: уникальный email адрес
    - password: хешированный пароль
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    bio = db.Column(db.String(160))  # Биография пользователя
    tweets = db.relationship('Tweet', backref='author', lazy='dynamic')
    # Подписки
    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic'
    )

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0

class Tweet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(280), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    likes = db.relationship('Like', backref='tweet', lazy='dynamic')

    def is_liked_by(self, user_id):
        return self.likes.filter_by(user_id=user_id).first() is not None

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tweet_id = db.Column(db.Integer, db.ForeignKey('tweet.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Создание всех таблиц в базе данных
def create_official_account():
    """Создание официального аккаунта и первого твита"""
    official_user = User.query.filter_by(username='TwitterClone').first()
    if not official_user:
        # Создаем официальный аккаунт
        hashed_password = generate_password_hash('secure_admin_password')
        official_user = User(
            username='TwitterClone',
            email='admin@twitterclone.com',
            password=hashed_password,
            bio='Официальный аккаунт Twitter Clone'
        )
        db.session.add(official_user)
        db.session.commit()

        # Создаем первый твит
        welcome_tweet = Tweet(
            content='Как дела? 👋 Добро пожаловать в Twitter Clone! Это первый твит на платформе.',
            user_id=official_user.id
        )
        db.session.add(welcome_tweet)
        db.session.commit()

def init_db():
    """Инициализация базы данных"""
    try:
        with app.app_context():
            db.create_all()
            create_official_account()
        print("База данных успешно инициализирована")
    except Exception as e:
        print(f"Ошибка при инициализации базы данных: {e}")

def check_db_integrity():
    """Проверка целостности базы данных"""
    try:
        with app.app_context():
            # Проверяем, что можем получить данные из каждой таблицы
            User.query.first()
            Tweet.query.first()
            Like.query.first()
        return True
    except Exception as e:
        print(f"Ош��бка при проверке базы данных: {e}")
        return False

# Инициализируем базу данных при запуске
with app.app_context():
    if not check_db_integrity():
        print("Проблема с базой данных. Попытка переинициализации...")
        init_db()
    else:
        print("База данных в порядке")

# Маршрут для главной страницы
@app.route('/')
def index():
    """Отображение главной страницы"""
    if not session.get('user_id'):
        return redirect(url_for('welcome'))
        
    tweets = []
    user = User.query.get(session['user_id'])
    # Получаем твиты от пользователя и тех, на кого он подписан
    followed_users = user.followed.all()
    followed_users.append(user)  # Добавляем твиты самого пользователя
    
    # Получаем также твиты от новостного бота
    news_bot = User.query.filter_by(username='gpt_news').first()
    if news_bot:
        followed_users.append(news_bot)
    
    tweets = Tweet.query.filter(Tweet.user_id.in_([u.id for u in followed_users])) \
                      .order_by(Tweet.timestamp.desc()).all()
    
    return render_template('index.html', tweets=tweets)

# Маршрут для регистрации
@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Обработка регистрации пользователя:
    GET: отображение формы регистрации
    POST: обработка данных формы регистрации
    """
    if request.method == 'POST':
        # Получение данных из формы
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Проверка совпадения паролей
        if password != confirm_password:
            flash('Пароли не совпадают')
            return redirect(url_for('register'))

        # Проверка существования пользователя с таким именем
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Пользователь с таким именем уже существует')
            return redirect(url_for('register'))

        # Проверка существования пользователя с таким email
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('Email уже используется')
            return redirect(url_for('register'))

        # Хеширование пароля и создание нового пользователя
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        # Создание сессии для нового пользователя
        session['user_id'] = new_user.id
        session['username'] = new_user.username
        return redirect(url_for('index'))

    # Отображение формы регистрации для GET запроса
    return render_template('register.html')

# Маршрут для входа в систему
@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Обработка входа пользователя:
    GET: отображение формы входа
    POST: проверка учетных данных и вход в систему
    """
    if request.method == 'POST':
        # Получение данных из формы
        username = request.form['username']
        password = request.form['password']

        # Поиск пользователя по имени или email
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()

        # Проверка пароля и создание сессии
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль')
            return redirect(url_for('login'))

    # Отображение формы входа для GET запроса
    return render_template('login.html')

# Маршрут для выхода из системы
@app.route('/logout')
def logout():
    """
    Выход пользователя из системы:
    - Удаление данных сессии
    - Перенаправление на главную страницу
    """
    session.pop('user_id', None)  # Удаление user_id из сессии
    session.pop('username', None)  # Удаление username из сессии
    return redirect(url_for('index'))

# Добавьте новый маршрут для создания твита
@app.route('/tweet', methods=['POST'])
def tweet():
    if 'user_id' not in session:
        flash('Необходимо войти в систему')
        return redirect(url_for('login'))
    
    try:
        content = request.form.get('content')
        if content and len(content) <= 280:
            tweet = Tweet(content=content, user_id=session['user_id'])
            db.session.add(tweet)
            db.session.commit()
            flash('Твит успешно создан')
        else:
            flash('Ошибка: твит не может быть пустым или длиннее 280 символов')
    except Exception as e:
        db.session.rollback()
        flash('Произошла ошибка при создании твита')
        print(f"Ошибка при создании твита: {e}")
    
    return redirect(url_for('index'))

# Добавим маршрут для лайков
@app.route('/like/<int:tweet_id>', methods=['POST'])
def like_tweet(tweet_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    existing_like = Like.query.filter_by(
        user_id=session['user_id'],
        tweet_id=tweet_id
    ).first()

    if existing_like:
        db.session.delete(existing_like)
    else:
        like = Like(user_id=session['user_id'], tweet_id=tweet_id)
        db.session.add(like)
    
    db.session.commit()
    return redirect(url_for('index'))

# Добавьте новый маршрут после существующих
@app.route('/welcome')
def welcome():
    """Страница приветствия для неавторизованных пользователей"""
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('welcome.html')

# Добавьте новый маршрут для профиля
@app.route('/profile/<username>', methods=['GET', 'POST'])
def profile(username):
    """Страница профиля пользователя"""
    # Получаем пользователя по имени
    profile_user = User.query.filter_by(username=username).first_or_404()
    
    # Если это POST запрос и пользователь редактирует свой профиль
    if request.method == 'POST' and session.get('user_id') == profile_user.id:
        bio = request.form.get('bio', '').strip()
        if len(bio) <= 160:  # Проверяем длину био
            profile_user.bio = bio
            db.session.commit()
            flash('Профиль обновлен')
        return redirect(url_for('profile', username=username))

    # Получаем твиты пользователя
    tweets = Tweet.query.filter_by(user_id=profile_user.id)\
                       .order_by(Tweet.timestamp.desc()).all()
    
    # Проверяем, подписан ли текущий пользователь на просматриваемый профиль
    is_following = False
    if session.get('user_id'):
        current_user = User.query.get(session['user_id'])
        is_following = current_user.is_following(profile_user)

    return render_template('profile.html', 
                         user=profile_user, 
                         tweets=tweets,
                         is_following=is_following)

# Добавьте маршруты для подписки/отписки
@app.route('/follow/<username>')
def follow(username):
    if not session.get('user_id'):
        return redirect(url_for('login'))
    
    user_to_follow = User.query.filter_by(username=username).first()
    if user_to_follow:
        current_user = User.query.get(session['user_id'])
        current_user.follow(user_to_follow)
        db.session.commit()
    
    return redirect(url_for('profile', username=username))

@app.route('/unfollow/<username>')
def unfollow(username):
    if not session.get('user_id'):
        return redirect(url_for('login'))
    
    user_to_unfollow = User.query.filter_by(username=username).first()
    if user_to_unfollow:
        current_user = User.query.get(session['user_id'])
        current_user.unfollow(user_to_unfollow)
        db.session.commit()
    
    return redirect(url_for('profile', username=username))

# Запуск приложения в режиме разработки
if __name__ == '__main__':
    app.run(debug=True)  # debug=True только для разработки! 