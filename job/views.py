from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from job.models import *
from job.utility import generate_structured_job_html, upload_job_post_to_wordpress
from seo_services.models import WordPressConnection
from .serializers import JobOnboardingFormSerializer
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from .models import ClientFeedback
from django.core.mail import send_mail
from django.conf import settings
from seo_services.models import OnboardingForm , BusinessLocation

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
    

class JobClosedAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        service_area = request.data.get("service_area")
        job_id = request.data.get("job_id")

        print("Job Closed from n8n:", email, service_area, job_id)
        feedback = ClientFeedback.objects.create(
            email=email,
            service_area=service_area,
            job_id=job_id
        )

        yes_url = f"{settings.FRONTEND_RESET_URL}job/feedback/{feedback.token}/yes/"
        no_url = f"{settings.FRONTEND_RESET_URL}job/feedback/{feedback.token}/no/"

        # Send email
        send_mail(
            subject="Are you satisfied with the service?",
            message=f"Please let us know:\nYes: {yes_url}\nNo: {no_url}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )

        return Response({"status": "email sent"})


class FeedbackAPI(APIView):
    def get(self, request, token, answer):
        try:
            feedback = ClientFeedback.objects.get(token=token)
        except ClientFeedback.DoesNotExist:
            return Response({"error": "Invalid or expired link"}, status=404)

        # Update feedback
        feedback.is_satisfied = (answer == "yes")
        feedback.save()

        # Base response
        response_data = {
            "satisfied": feedback.is_satisfied,
            "email": feedback.email,
            "job_id": feedback.job_id,
            "service_area": feedback.service_area,
        }

        if feedback.is_satisfied:
            # Now find business location using service_area + user
            onboarding_form = OnboardingForm.objects.filter(email=feedback.email).first()
            if onboarding_form:
                location = BusinessLocation.objects.filter(onboarding_form=onboarding_form).first()
                if location:
                    response_data["review_url"] = location.location_url
        else:
            response_data["feedback_url"] = "https://your-feedback-form.com"

        return Response(response_data, status=200)
