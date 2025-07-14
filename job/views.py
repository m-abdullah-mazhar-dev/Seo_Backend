from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from job.models import JobOnboardingForm, JobPage
from job.utility import generate_structured_job_html, upload_job_post_to_wordpress
from seo_services.models import WordPressConnection
from .serializers import JobOnboardingFormSerializer
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

class CreateJobOnboardingFormAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        serializer = JobOnboardingFormSerializer(data=request.data)
        if serializer.is_valid():
            job_form = serializer.save()

            job_page = JobPage.objects.filter(user=request.user).last()
            if not job_page:
                return Response({"error": "No job page submitted for this user."}, status=400)
            
            try:
                html_content = generate_structured_job_html(job_form)
                upload_job_post_to_wordpress(job_form, job_page, html_content)
            except Exception as e:
                return Response({"error": f"Failed to publish job: {str(e)}"}, status=500)

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
    

class SubmitJobPageAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        page_url = request.data.get("page_url")

        if not page_url:
            return Response({"error": "Page URL is required."}, status=400)

        try:
            wp_conn = user.wordpress_connection
        except WordPressConnection.DoesNotExist:
            return Response({"error": "User has not connected WordPress."}, status=400)

        job_page = JobPage.objects.create(
            user=user,
            wordpress_connection=wp_conn,
            page_url=page_url
        )

        return Response({"message": "Job page submitted successfully."})
