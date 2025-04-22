from app.extensions import ma
from app.models import User

class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_instance = True
        # Exclude sensitive information like password hash from API responses
        exclude = ("password_hash",)
        # Make email and username load_only for registration/login, not dumping
        load_only = ("password",) # Temporary field for password input

    # If you need custom fields or validation, add them here
    # e.g., password = ma.Str(required=True, load_only=True) # Handled in routes usually
