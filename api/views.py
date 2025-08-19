from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status, generics
from accounts.models import User, CompanyLinkedInAuth, Company, Branch, Department
from .models import JobDetails, Role, UserRoles
from accounts.serializers import UserWithRolesPermissionsSerializer, CSVUserSerializer, UserSerializer
from .serializers import RoleCreateSerializer, PermissionCreateSerializer, AssignPermissionToRoleSerializer, AssignRoleToUserSerializer, JobDetailsSerializer, JobListSerializer
from rest_framework import status, permissions
from .pagination import CustomPageNumberPagination
from django.utils.timezone import now
from datetime import timedelta
import requests
from rest_framework.parsers import MultiPartParser
from io import TextIOWrapper
import csv
from .utils import generate_random_password
from api.tasks import send_invitation_email_task







class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"message": f"Welcome {request.user.fname} to your dashboard!"})
    

class UserDetailWithRolesPermissions(APIView):
    def get(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        serializer = UserWithRolesPermissionsSerializer(user)
        return Response(serializer.data)


class CreateRoleView(APIView):
    def post(self, request):
        serializer = RoleCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CreatePermissionView(APIView):
    def post(self, request):
        serializer = PermissionCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
class AssignPermissionToRoleView(APIView):
    def post(self, request):
        serializer = AssignPermissionToRoleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Permission assigned to role successfully."}, status=201)
        return Response(serializer.errors, status=400)



class AssignRoleToUserView(APIView):
    def post(self, request):
        serializer = AssignRoleToUserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Role assigned to user successfully."}, status=201)
        return Response(serializer.errors, status=400)




class CreateJobPostView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = JobDetailsSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            data = serializer.validated_data

            # Extract description, requirements, and department name
            description = data.pop('job_description')
            requirements = data.pop('job_requirements')
            department = data.pop('department')

            user = request.user
            company = getattr(user, 'company', None)
            branch = getattr(user, 'branch', None)

            if not company:
                return Response({'detail': 'User does not have an associated company.'}, status=status.HTTP_400_BAD_REQUEST)

            if not branch:
                return Response({'detail': 'User does not have an associated branch.'}, status=status.HTTP_400_BAD_REQUEST)

            # Get or create department in this branch
            department, _ = Department.objects.get_or_create(name=department, branch=branch)

            # Create JobDetails
            job = JobDetails.objects.create(
                **data,
                description=description,
                requirements=requirements,
                posted_by=user,
                company=company,
                branch=branch,
                department=department,
                status='active',
                job_deadline=now() + timedelta(days=30),
            )

            return Response({'message': 'Job posted successfully', 'job_id': job.id}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class ListJobView(generics.ListAPIView):
    queryset = JobDetails.objects.all().order_by('-created_at')
    serializer_class = JobListSerializer
    permission_classes = [AllowAny]
    pagination_class = CustomPageNumberPagination
    


class PostJobToLinkedInView(APIView):
    def post(self, request):
        job_id = request.data.get('job_id')
        if not job_id:
            return Response({"error": "Job ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            job = JobDetails.objects.select_related('company').get(id=job_id)
            company = job.company
            linkedin_auth = company.linkedin_auth
        except JobDetails.DoesNotExist:
            return Response({"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)
        except CompanyLinkedInAuth.DoesNotExist:
            return Response({"error": "LinkedIn auth not found for the company"}, status=status.HTTP_404_NOT_FOUND)

        # Construct job URL
        # job_url = f"https://yourfrontend.com/jobs/{job.id}"
        job_url = f"http://localhost:8080/application"

        # Format LinkedIn post payload
        payload = {
            "author": linkedin_auth.person_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": f"""✨ We're hiring a {job.job_title} at {company.name}! 🚀

📍 Location: {job.city}, {job.country}
💼 Type: {job.job_type}
💰 Salary: {job.salary_from} - {job.salary_to} {job.currency} per {job.period}

📝 Apply now: {job_url}
"""
                    },
                    "shareMediaCategory": "ARTICLE",
                    "media": [
                        {
                            "status": "READY",
                            "description": {
                                "text": job.description or "Exciting opportunity to join our team!"
                            },
                            "originalUrl": job_url,
                            "title": {
                                "text": f"Job Opening: {job.job_title} at {company.name}"
                            }
                        }
                    ]
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }

        # Make request to LinkedIn
        headers = {
            "Authorization": f"Bearer {linkedin_auth.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }

        response = requests.post("https://api.linkedin.com/v2/ugcPosts", json=payload, headers=headers)

        if response.status_code == 201:
            return Response({"message": "Job posted successfully on LinkedIn."}, status=status.HTTP_201_CREATED)
        else:
            return Response({
                "error": "Failed to post job to LinkedIn.",
                "details": response.json()
            }, status=response.status_code)
    



class EmployeeCSVImportView(APIView):
    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        print("EmployeeCSVImportView-----------------------")
        csv_file = request.FILES.get('file')
        if not csv_file:
            return Response({"detail": "No CSV file uploaded."}, status=400)

        decoded_file = TextIOWrapper(csv_file.file, encoding='utf-8')
        reader = csv.DictReader(decoded_file)

        created_users = []
        updated_users = []

        company = request.user.company
        branch = request.user.branch

        for row in reader:
            role_name = row.pop('role', '').strip()
            email = row.get('email')

            if not email:
                continue

            try:
                existing_user = User.objects.get(email=email)
                for field in ['fname', 'lname', 'phone']:
                    if row.get(field):
                        setattr(existing_user, field, row[field])
                existing_user.company = company
                existing_user.branch = branch
                existing_user.save()
                updated_users.append(email)
                user_instance = existing_user
            except User.DoesNotExist:
                serializer = CSVUserSerializer(data=row)
                if serializer.is_valid():
                    temp_password = generate_random_password()
                    user_instance = serializer.save(company=company, branch=branch)
                    user_instance.set_password(temp_password)
                    user_instance.save()
                    
                    # Call Celery async task
                    send_invitation_email_task.delay(
                        user_instance.email,
                        user_instance.fname,
                        temp_password
                    )
                    
                    created_users.append(email)
                else:
                    return Response({
                        "detail": f"Invalid data for user {email}",
                        "errors": serializer.errors,
                        "row_data": row
                    }, status=400)

            if role_name:
                role_obj, _ = Role.objects.get_or_create(name=role_name)
                UserRoles.objects.get_or_create(user=user_instance, role=role_obj)

        return Response({
            "detail": f"{len(created_users)} users created, {len(updated_users)} updated.",
            "created": created_users,
            "updated": updated_users
        }, status=201)





class CompanyUsersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not user.company:
            return Response({"detail": "User is not assigned to a company."}, status=400)

        users = User.objects.filter(company=user.company)
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

