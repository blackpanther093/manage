import os
from app import create_app

env = os.getenv('FLASK_CONFIG', 'production')
app = create_app(env)

if __name__ == '__main__':
    if env == 'production':
        print("WARNING: Use a production WSGI server like Gunicorn")
    else:
        app.run(
            host='0.0.0.0',
            port=int(os.getenv('PORT', 5000)),
            debug=app.config.get('DEBUG', False),
            use_reloader=False
        )
