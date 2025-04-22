from flask import Blueprint, request, jsonify
from app.models import User
from app.schemas import UserSchema
from app.extensions import db, bcrypt
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from marshmallow import ValidationError

bp = Blueprint('auth', __name__)
user_schema = UserSchema()
users_schema = UserSchema(many=True) # For listing (admin only?)

@bp.route('/register', methods=['POST'])
def register():
    json_data = request.get_json()
    if not json_data:
        return jsonify({"message": "No input data provided"}), 400

    # Basic validation (can use Marshmallow schema load for more complex validation)
    if not all(k in json_data for k in ('username', 'email', 'password')):
         return jsonify({"message": "Missing username, email, or password"}), 400

    # Check if user already exists
    if User.query.filter((User.username == json_data['username']) | (User.email == json_data['email'])).first():
        return jsonify({"message": "Username or email already exists"}), 409

    try:
        # Create new user instance (without password initially)
        new_user = User(
            username=json_data['username'],
            email=json_data['email']
        )
        new_user.set_password(json_data['password']) # Hash password

        db.session.add(new_user)
        db.session.commit()

        # Don't return password hash
        result = user_schema.dump(new_user)
        return jsonify(result), 201

    except Exception as e: # Catch potential DB errors
        db.session.rollback()
        return jsonify({"message": "Could not register user", "error": str(e)}), 500


@bp.route('/login', methods=['POST'])
def login():
    json_data = request.get_json()
    if not json_data:
        return jsonify({"message": "No input data provided"}), 400

    if 'username' not in json_data or 'password' not in json_data:
        return jsonify({"message": "Missing username or password"}), 400

    user = User.query.filter_by(username=json_data['username']).first()

    if user and user.check_password(json_data['password']):
        # Identity can be user ID or any unique identifier
        access_token = create_access_token(identity=str(user.id))
        return jsonify(access_token=access_token), 200
    else:
        return jsonify({"message": "Invalid username or password"}), 401

@bp.route('/me', methods=['GET'])
@jwt_required() # Protect this route
def get_current_user():
    current_user_id = int(get_jwt_identity())
    user = db.session.get(User, current_user_id)
    if not user:
         return jsonify({"message": "User not found"}), 404
    return jsonify(user_schema.dump(user)), 200

# Add refresh token endpoint if needed
