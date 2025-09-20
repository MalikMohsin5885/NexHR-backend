from rest_framework import serializers
from .models import Role, Permission, RolePermissions, JobDetails
from accounts.models import User
from api.models import UserRoles

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'name', 'description']

class RoleWithPermissionsSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ['id', 'name', 'description', 'permissions']

    def get_permissions(self, obj):
        role_permissions = RolePermissions.objects.filter(role=obj).select_related('permission')
        permissions = [rp.permission for rp in role_permissions]
        return PermissionSerializer(permissions, many=True).data


class RoleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'name', 'description']

class PermissionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'name', 'description']


class AssignPermissionToRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolePermissions
        fields = ['role', 'permission']

    def validate(self, data):
        if RolePermissions.objects.filter(role=data['role'], permission=data['permission']).exists():
            raise serializers.ValidationError("This permission is already assigned to the role.")
        return data

class AssignRoleToUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRoles
        fields = ['user', 'role']

    def validate(self, data):
        if UserRoles.objects.filter(user=data['user'], role=data['role']).exists():
            raise serializers.ValidationError("This role is already assigned to the user.")
        return data
    
class JobDetailsSerializer(serializers.ModelSerializer):
    job_description = serializers.CharField(write_only=True)
    job_requirements = serializers.CharField(write_only=True)
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
        ]

    def validate(self, data):
        return data
    


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

