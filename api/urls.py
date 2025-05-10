from django.urls import path
from .views import (
    DashboardView,
    UserDetailWithRolesPermissions,
    CreateRoleView,
    CreatePermissionView,
    AssignRoleToUserView,
    AssignPermissionToRoleView
)
urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    
    path('user/<int:pk>/roles-permissions/', UserDetailWithRolesPermissions.as_view(), name='user-roles-permissions'),
    path('roles/create/', CreateRoleView.as_view(), name='create-role'),
    path('permissions/create/', CreatePermissionView.as_view(), name='create-permission'),
    
    path('roles/assign-permission/', AssignPermissionToRoleView.as_view(), name='assign-permission-to-role'),
    path('users/assign-role/', AssignRoleToUserView.as_view(), name='assign-role-to-user'),

]
