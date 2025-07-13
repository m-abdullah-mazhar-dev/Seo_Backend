from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate

from .serializers import UserSerializer, UserLoginSerializer

from rest_framework_simplejwt.tokens import RefreshToken

from rest_framework.permissions import IsAuthenticated
from .serializers import ChangePasswordSerializer

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)

    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


# Create your views here.

class RegisterApi(APIView):
    def post(self,request):
        data = request.data
        serializers = UserSerializer(data = data)
        if serializers.is_valid():
            user = serializers.save()
            token = get_tokens_for_user(user)
            return Response({"token":token, "msg":"registration success"}, status=status.HTTP_201_CREATED)
        return Response(serializers.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLoginApi(APIView):
    def post(self,request):
        serializer = UserLoginSerializer(data = request.data)
        if serializer.is_valid(raise_exception=True):
            email = serializer.validated_data.get('email')
            password = serializer.validated_data.get('password')

            user = authenticate(email=email, password=password)
            print(user, "--------")

            if user is not None:
                token = get_tokens_for_user(user)
                return Response({"token":token,"msg": "login success"} ,status= status.HTTP_200_OK)
            else:
                return Response({"errors":{"non_field_errors":["password or email is not valid"]}}, status= status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status= status.HTTP_400_BAD_REQUEST)



class ChangePasswordApi(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({"msg": "Password changed successfully"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
