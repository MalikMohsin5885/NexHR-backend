from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, permissions
from .serializers import JobDetailsSerializer, JobListSerializer, JobApplicationSerializer, RequiredSkillSerializer
from accounts.serializers import CSVUserSerializer
from accounts.models import User, CompanyLinkedInAuth, Department
from .models import JobDetails, JobApplication, RequiredSkill, CandidateSkill, CandidateExperience, CandidateEducation
from .pagination import CustomPageNumberPagination
from rest_framework.parsers import MultiPartParser
from io import TextIOWrapper
import csv
from .utils import generate_random_password, extract_text_from_file
from .tasks import send_invitation_email_task, embed_job_description, embed_application_profile, screen_job_after_deadline
from datetime import timedelta
from django.utils.timezone import now
import requests
from api.models import Role, UserRoles
import json




# Create your views here.

# -------------------- Skills List/Search API --------------------
class RequiredSkillListView(generics.ListAPIView):
    serializer_class = RequiredSkillSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = RequiredSkill.objects.all().order_by("name")
        search = self.request.query_params.get("q")
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset[:10]


class CreateJobPostView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        print("resquest data-------------------",request.data)
        serializer = JobDetailsSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            data = serializer.validated_data

            # Extract extra fields
            description = data.pop('job_description')
            requirements = data.pop('job_requirements', None)
            department_name = data.pop('department')
            job_deadline = data.pop('job_deadline')   # ✅ from payload
            skill_names = data.pop('required_skills', [])
            print("Job Deadline-=-=-=-:", job_deadline)

            user = request.user
            company = getattr(user, 'company', None)
            branch = getattr(user, 'branch', None)

            if not company:
                return Response({'detail': 'User does not have an associated company.'}, status=status.HTTP_400_BAD_REQUEST)

            if not branch:
                return Response({'detail': 'User does not have an associated branch.'}, status=status.HTTP_400_BAD_REQUEST)

            # Get or create department in this branch
            department, _ = Department.objects.get_or_create(name=department_name, branch=branch)

            # Create JobDetails
            job = JobDetails.objects.create(
                **data,
                description=description,
                posted_by=user,
                company=company,
                branch=branch,
                department=department,
                status='active',
                job_deadline=job_deadline, 
            )
            
            # Handle required skills (create if missing)
            skills_to_add = []
            for name in skill_names:
                if name:  # avoid None
                    skill, _ = RequiredSkill.objects.get_or_create(name=name)
                    skills_to_add.append(skill)
            if skills_to_add:
                job.required_skills.add(*skills_to_add)
                
            
            print("Job Deadline:", job.job_deadline)
            # If you want to store requirements, add a field in model OR keep it in job_schema
            if requirements:
                job.job_schema['requirements'] = requirements
                job.save()

            # ASAP embed JD so it's ready when deadline passes
            embed_job_description.delay(job.id)

            print(f"[View] Job {job.id} created and embedding queued")
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
        
class JobApplicationView(APIView):
    def post(self, request, *args, **kwargs):
        print("========== RAW REQUEST DATA ==========")
        print("request.data:", request.data)
        print("request.FILES:", request.FILES)

        # Convert QueryDict -> normal dict with lists unwrapped
        data = {}
        for key, value in request.data.items():
            if key in ["skills", "experiences", "educations"]:
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        data[key] = parsed   # ✅ store clean list
                    else:
                        data[key] = []
                except Exception as e:
                    print(f"[ERROR] Failed parsing {key}: {e}")
                    data[key] = []
            else:
                data[key] = value

        resume_file = request.FILES.get("resume")
        if resume_file:
            print("[DEBUG] Resume file received:", resume_file.name)
            resume_text = extract_text_from_file(resume_file)
            data["resume_text"] = resume_text
        else:
            data["resume_text"] = ""

        print("========== FINAL CLEAN DATA SENT TO SERIALIZER ==========")
        print(data)

        serializer = JobApplicationSerializer(data=data)
        if serializer.is_valid():
            app = serializer.save()
            print(f"[SUCCESS] Application {app.id} created successfully")
            print("[DEBUG] Skills saved:", CandidateSkill.objects.filter(application=app).values())
            print("[DEBUG] Experiences saved:", CandidateExperience.objects.filter(application=app).values())
            print("[DEBUG] Educations saved:", CandidateEducation.objects.filter(application=app).values())

            embed_application_profile.delay(app.id)  # queue embedding
            return Response(JobApplicationSerializer(app).data, status=status.HTTP_201_CREATED)

        print("[ERROR] Serializer validation failed:", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RunScreeningNowView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, job_id):
        screen_job_after_deadline.delay(job_id)
        return Response(
            {"message": f"Screening queued for job {job_id}"},
            status=status.HTTP_200_OK
        )

