from django.urls import path
from .views import (
    DashboardView,
    UserDetailWithRolesPermissions,
    CreateRoleView,
    CreatePermissionView,
    AssignRoleToUserView,
    AssignPermissionToRoleView, 
    CompanyUsersView
)
from recruitment.views import (
    CreateJobPostView, 
    ListJobView,
    PostJobToLinkedInView, 
    EmployeeCSVImportView,
    JobApplicationView,
    RunScreeningNowView, 
)
urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    
    path('user/<int:pk>/roles-permissions/', UserDetailWithRolesPermissions.as_view(), name='user-roles-permissions'),
    path('roles/create/', CreateRoleView.as_view(), name='create-role'),
    path('permissions/create/', CreatePermissionView.as_view(), name='create-permission'),
    
    path('roles/assign-permission/', AssignPermissionToRoleView.as_view(), name='assign-permission-to-role'),
    path('users/assign-role/', AssignRoleToUserView.as_view(), name='assign-role-to-user'),
    
    path('jobs/post/', CreateJobPostView.as_view(), name='job-post'),
    path('jobs/list/', ListJobView.as_view(), name='jobs-list'),
    
    path('post-job-linkedin/', PostJobToLinkedInView.as_view(), name='post-job-linkedin'),
    
    
    path('applications/', JobApplicationView.as_view(), name='job-application-create'),
    
    path("jobs/<int:job_id>/screen/", RunScreeningNowView.as_view(), name="job-screen-now"),
    
    path('import-employees/', EmployeeCSVImportView.as_view(), name='import-employees'),
    path('company-users/', CompanyUsersView.as_view(), name='company-users'),
]
