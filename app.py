from flask import Flask, jsonify
from flask_cors import CORS
from routes.auth_routes import auth
from routes.db_routes import db_routes
from routes.chatbot_routes import chatbot_routes

app = Flask(__name__)

# Configure CORS to allow your frontend origin
CORS(app, 
     origins=["http://127.0.0.1:5505", "http://localhost:5505", "http://127.0.0.1:5500", "http://localhost:5500"],
     supports_credentials=True,
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"])

# Global error handler to catch all exceptions
@app.errorhandler(Exception)
def handle_exception(e):
    import traceback
    print("=" * 50)
    print("500 ERROR - Full Traceback:")
    print("=" * 50)
    print(traceback.format_exc())
    print("=" * 50)
    return jsonify({"error": str(e)}), 500

# Register blueprints
app.register_blueprint(auth)
app.register_blueprint(db_routes)
app.register_blueprint(chatbot_routes)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
