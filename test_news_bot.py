from app import app, db, User, Tweet
from werkzeug.security import generate_password_hash
from datetime import datetime
import random

# Конфигурация новостного бота
NEWS_BOT = {
    'username': 'gpt_news',
    'email': 'news@twitterclone.com',
    'password': 'secure_news_password',
    'bio': '🤖 Автоматический новостной бот | Актуальные новости каждые 30 минут'
}

SAMPLE_NEWS = [
    "🌍 Новые технологии в борьбе с изменением климата: ученые представили инновационное решение",
    "💡 Прорыв в квантовых вычислениях: создан новый тип кубита",
    "🚀 SpaceX анонсировала новую миссию на Марс",
    "🤖 Искусственный интеллект научился предсказывать погоду точнее метеорологов",
    "📱 Представлено новое поколение смартфонов с революционной технологией",
    "🌐 Интернет будущего: представлен новый протокол передачи данных",
    "🎮 Игровая индустрия: основные тренды года",
    "💊 Прорыв в медицине: новый метод лечения распространенных заболеваний",
    "🌱 Экологичные технологии: как изменится транспорт будущего",
    "📚 Образование будущего: как технологии меняют процесс обучения"
]

def get_news():
    """Получение случайной новости с временной меткой"""
    news_text = random.choice(SAMPLE_NEWS)
    current_time = datetime.now().strftime('%H:%M')
    return f"{news_text}\n\nОпубликовано в {current_time}"

def test_bot():
    with app.app_context():
        # Проверяем существование бота
        bot = User.query.filter_by(username=NEWS_BOT['username']).first()
        if not bot:
            print("Создаем нового бота...")
            bot = User(
                username=NEWS_BOT['username'],
                email=NEWS_BOT['email'],
                password=generate_password_hash(NEWS_BOT['password']),
                bio=NEWS_BOT['bio']
            )
            db.session.add(bot)
            db.session.commit()
        
        # Публикуем тестовое сообщение
        test_tweet = Tweet(
            content=get_news(),
            user_id=bot.id,
            timestamp=datetime.utcnow()
        )
        db.session.add(test_tweet)
        db.session.commit()
        
        # Проверяем, что твит создался
        latest_tweet = Tweet.query.filter_by(user_id=bot.id).order_by(Tweet.timestamp.desc()).first()
        if latest_tweet:
            print(f"Успешно создан твит: {latest_tweet.content}")
        else:
            print("Ошибка: твит не создан")

if __name__ == '__main__':
    test_bot() 