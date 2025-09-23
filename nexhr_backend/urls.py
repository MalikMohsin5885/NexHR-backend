from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

def health_check(request):
    """Simple health check endpoint for Cloud Run"""
    return JsonResponse({"status": "ok", "service": "nexhr-backend"})

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path('api/', include('api.urls')),
    path('health/', health_check, name='health_check'),
    
    # path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    # path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]