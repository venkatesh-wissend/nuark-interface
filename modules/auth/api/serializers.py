from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from modules.auth.models.auth_user import AuthUser
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


# -------------------------
# Register Serializer
# -------------------------
class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthUser
        fields = ["id", "username", "password", "email", "first_name", "last_name", "account_id"]
        extra_kwargs = {
            "password": {"write_only": True}
        }

    def create(self, validated_data):
        validated_data["password"] = make_password(validated_data["password"])
        return AuthUser.objects.create(**validated_data)

    # ⭐ CUSTOM RESPONSE FORMAT HERE
    def to_representation(self, instance):
        return {
            "status": True,
            "statusCode": 201,
            "message": "User registered successfully",
            "data": {
                "id": instance.id,
                "username": instance.username,
                "email": instance.email,
                "first_name": instance.first_name,
                "last_name": instance.last_name,
                "account_id": instance.account_id
            }
        }


# -------------------------
# Custom Login Serializer
# -------------------------
class CustomTokenSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        token["email"] = user.email
        token["user_id"] = user.id
        token["account_id"] = user.account_id
        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        return {
            "status": True,
            "statusCode": 200,
            "message": "Login successful",
            "data": {
                "accessToken": data["access"],
                "user": {
                    "id": self.user.id,
                    "username": self.user.username,
                    "email": self.user.email,
                    "account_id": self.user.account_id,
                }
            }
        }

