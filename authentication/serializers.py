from rest_framework import serializers
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.conf import settings
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth import get_user_model
User = get_user_model()



def validate_password_strength(password):
    if len(password) < 8:
        raise serializers.ValidationError("Password must be at least 8 characters long.")

class UserSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(style = {'input_type': 'password'}, write_only = True)
    class Meta:
        model = User
        fields = ["first_name" ,"last_name","email", "phone_number","password", "password2"]

    def validate(self, attrs):

        # Lowercase the email
        if "email" in attrs and attrs["email"]:
            attrs["email"] = attrs["email"].lower()

        password = attrs.get("password")
        password2 = attrs.get('password2')

        if password != password2:
            raise serializers.ValidationError("password not matched")
        
        
        validate_password_strength(password)

        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        return User.objects.create_user(**validated_data)



class UserLoginSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length = 255)
    class Meta:
        model = User
        fields = ["email", "password"]
        


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirm_password = serializers.CharField(required=True)

    def validate(self, attrs):
        user = self.context['request'].user
        old_password = attrs.get('old_password')
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')

        if not user.check_password(old_password):
            raise serializers.ValidationError({"old_password": "Old password is not correct"})

        if new_password != confirm_password:
            raise serializers.ValidationError({"confirm_password": "New passwords do not match"})

        if old_password == new_password:
            raise serializers.ValidationError({"new_password": "New password must be different from the old one"})
        
        validate_password_strength(new_password)

        return attrs

class SendPasswordResetEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        email = attrs.get("email")
        if not User.objects.filter(email=email).exists():
            raise serializers.ValidationError("User with this email doesn't exist")

        user = User.objects.get(email=email)
        uid = urlsafe_base64_encode(force_bytes(user.id))
        token = PasswordResetTokenGenerator().make_token(user)
        print(settings.FRONTEND_RESET_URL)
        reset_url = f"{settings.FRONTEND_RESET_URL}{uid}.{token}"

        subject = "Reset Your Password"
        message = f"Hi {user.first_name},\n\nClick the link below to reset your password:\n{reset_url}\n\nIf you didn't request this, ignore this email."

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        return attrs
    


class ResetPasswordSerializer(serializers.Serializer):
    uid_token = serializers.CharField()
    new_password = serializers.CharField()
    confirm_password = serializers.CharField()

    def validate(self, attrs):
        uid_token = attrs.get("uid_token")
        new_password = attrs.get("new_password")
        confirm_password = attrs.get("confirm_password")

        try:
            uidb64, token = uid_token.split(".")
            user_id = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(id=user_id)
        except Exception:
            raise serializers.ValidationError("Invalid or expired token")

        if not PasswordResetTokenGenerator().check_token(user, token):
            raise serializers.ValidationError("Invalid or expired token")

        if new_password != confirm_password:
            raise serializers.ValidationError("Passwords do not match")

        validate_password_strength(new_password)

        user.set_password(new_password)
        user.save()

        return attrs
