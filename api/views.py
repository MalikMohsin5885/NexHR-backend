from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from accounts.models import User
from accounts.serializers import UserWithRolesPermissionsSerializer
from .serializers import RoleCreateSerializer, PermissionCreateSerializer, AssignPermissionToRoleSerializer, AssignRoleToUserSerializer


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
