"""
Application entry point for ManageIt
"""
import os
from app import create_app
from app.config import config

# Get configuration from environment
config_name = os.getenv('FLASK_CONFIG', 'default')
app = create_app(config[config_name])

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host="0.0.0.0", port=port, debug=debug)
