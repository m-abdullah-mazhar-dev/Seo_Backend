from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from job.models import JobOnboardingForm
from .serializers import JobOnboardingFormSerializer
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

class CreateJobOnboardingFormAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        serializer = JobOnboardingFormSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Onboarding form created successfully",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            "message": "Form submission failed",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def get(self, request, pk=None, format=None):
        if pk:
            form = get_object_or_404(JobOnboardingForm, pk=pk)
            serializer = JobOnboardingFormSerializer(form)
            return Response({
                "message": f"Onboarding form ID {pk} fetched successfully",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        else:
            forms = JobOnboardingForm.objects.all()
            serializer = JobOnboardingFormSerializer(forms, many=True)
            return Response({
                "message": "All onboarding forms fetched successfully",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        
    def patch(self, request, pk, format=None):
        try:
            instance = JobOnboardingForm.objects.get(pk=pk)
        except JobOnboardingForm.DoesNotExist:
            return Response({
                "message": f"Onboarding form with ID {pk} does not exist."
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = JobOnboardingFormSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": f"Onboarding form ID {pk} updated successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        return Response({
            "message": "Update failed due to invalid data.",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    

