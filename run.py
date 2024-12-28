from app import app

if __name__ == '__main__':
    # Запуск приложения в режиме отладки
    # В продакшене установите debug=False
    app.run(debug=True, host='0.0.0.0', port=5000) 