from rest_framework import serializers
from django.contrib.auth import get_user_model
User = get_user_model()


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

        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        return User.objects.create_user(**validated_data)



class UserLoginSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length = 255)
    class Meta:
        model = User
        fields = ["email", "password"]
        