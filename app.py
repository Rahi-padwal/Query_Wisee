from flask import Flask
from flask_cors import CORS
from routes.auth_routes import auth
from routes.db_routes import db_routes
from routes.chatbot_routes import chatbot_routes

app = Flask(__name__)
CORS(app, supports_credentials=True)

# Register blueprints
app.register_blueprint(auth)
app.register_blueprint(db_routes)
app.register_blueprint(chatbot_routes)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
