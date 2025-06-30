from flask import Flask, jsonify
from flask_cors import CORS
from routes.auth_routes import auth
from routes.db_routes import db_routes
from routes.chatbot_routes import chatbot_routes

app = Flask(__name__)

# Configure CORS to allow all origins
CORS(app, 
     origins=["*"],
     supports_credentials=True,
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"])

# Register blueprints
app.register_blueprint(auth)
app.register_blueprint(db_routes)
app.register_blueprint(chatbot_routes)

if __name__ == '__main__':
    app.run(port=5501)
