from .models import JobDetails, JobApplication, CandidateSkill, CandidateExperience, CandidateEducation, RequiredSkill
from rest_framework import serializers
from django.utils.timezone import now


class RequiredSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequiredSkill
        fields = ['id', 'name']


class SkillField(serializers.Field):
    def to_internal_value(self, data):
        if isinstance(data, dict):
            return data.get("name")  # take the "name" value
        elif isinstance(data, str):
            return data
        raise serializers.ValidationError("Skill must be a string or an object with 'name'")

    def to_representation(self, value):
        # When returning, show full object again (id + name)
        return {"id": value.id, "name": value.name}

class JobDetailsSerializer(serializers.ModelSerializer):
    job_description = serializers.CharField(write_only=True)
    department = serializers.CharField(write_only=True)

    required_skills = serializers.ListField(
        child=SkillField(),
        required=False
    )

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
            'job_schema',
            'experience_level',
            'department',
            'job_deadline',
            'required_skills',
        ]

    def validate_job_deadline(self, value):
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

    def create(self, validated_data):
        skills_data = validated_data.pop('skills', [])
        experiences_data = validated_data.pop('experiences', [])
        educations_data = validated_data.pop('educations', [])

        application = JobApplication.objects.create(**validated_data)

        # Save related skills
        for skill in skills_data:
            CandidateSkill.objects.create(application=application, **skill)

        # Save related experiences
        for exp in experiences_data:
            CandidateExperience.objects.create(application=application, **exp)

        # Save related educations
        for edu in educations_data:
            CandidateEducation.objects.create(application=application, **edu)

        return application