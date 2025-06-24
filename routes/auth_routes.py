# auth_routes.py
from flask import Blueprint, request, jsonify
from routes.user_model import register_user, validate_user

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['POST'])
def register():
    data = request.json
    if register_user(data['username'], data['email'], data['password']):
        return jsonify({"message": "Registered successfully"}), 201
    return jsonify({"error": "User already exists"}), 409

@auth.route('/login', methods=['POST'])
def login():
    data = request.json
    user = validate_user(data['email'], data['password'])
    if user:
        # Return the full user object (excluding sensitive data)
        user_response = {
            'user_id': user['user_id'],
            'username': user['username'],
            'email': user['email']
        }
        return jsonify({"message": "Login successful", "user": user_response}), 200
    return jsonify({"error": "Invalid credentials"}), 401
