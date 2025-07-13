from rest_framework import serializers
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
