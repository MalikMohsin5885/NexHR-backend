from rest_framework import serializers
from .models import Role, Permission, RolePermissions
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
