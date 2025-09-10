from .models import JobDetails, JobApplication, CandidateSkill, CandidateExperience, CandidateEducation
from rest_framework import serializers

class JobDetailsSerializer(serializers.ModelSerializer):
    job_description = serializers.CharField(write_only=True)
    job_requirements = serializers.CharField(write_only=True, required=False)  # optional
    department = serializers.CharField(write_only=True)

    class Meta:
        model = JobDetails
        fields = [
            'id',
            'job_title',
            'job_type',
            'location_type',
            'city',
            'state',
            'country',
            'salary_from',
            'salary_to',
            'currency',
            'period',
            'job_description',
            'job_requirements',
            'job_schema',
            'experience_level',
            'department',
            'job_deadline',   # ✅ accept datetime from payload
        ]

    def validate_job_deadline(self, value):
        from django.utils.timezone import now
        if value <= now():
            raise serializers.ValidationError("Deadline must be in the future.")
        return value

class JobListSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = JobDetails
        fields = [
            'job_title', 'department', 'experience_level',
            'salary_from', 'salary_to', 'currency', 'created_at',
            'period', 'city', 'state', 'country', 'job_deadline',
            'company_name' 
        ]
        
        

class CandidateSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateSkill
        fields = ['id', 'name']


class CandidateExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateExperience
        fields = ['id', 'years_of_experience', 'previous_job_titles', 'company_name']


class CandidateEducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateEducation
        fields = [
            'id',
            'education_level',
            'institution_name',
            'degree_detail',
            'grades',
            'start_date',
            'end_date',
            'description'
        ]
        



class JobApplicationSerializer(serializers.ModelSerializer):
    skills = CandidateSkillSerializer(many=True, required=False)
    experiences = CandidateExperienceSerializer(many=True, required=False)
    educations = CandidateEducationSerializer(many=True, required=False)

    class Meta:
        model = JobApplication
        fields = [
            'id', 'job', 'candidate_fname', 'candidate_lname', 'email', 'phone',
            'status', 'applied_at', 'gender', 'address', 'dob',
            'resume_text', 'skills', 'experiences', 'educations'
        ]
        # remove 'resume_text' from read_only_fields

    def create(self, validated_data):
        skills_data = validated_data.pop('skills', [])
        experiences_data = validated_data.pop('experiences', [])
        educations_data = validated_data.pop('educations', [])

        application = JobApplication.objects.create(**validated_data)

        for skill in skills_data:
            CandidateSkill.objects.create(application_id=application, **skill)

        for exp in experiences_data:
            CandidateExperience.objects.create(application_id=application, **exp)

        for edu in educations_data:
            CandidateEducation.objects.create(application_id=application, **edu)

        return application

