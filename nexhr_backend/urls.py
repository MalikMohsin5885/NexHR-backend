from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

# ⬇️ ADD THESE IMPORTS
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

def root_health(_request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path('api/', include('api.urls')),
    path("api/payroll/", include("payroll.urls")),
    path('', root_health),
    path('api-auth/', include('rest_framework.urls')),  # browsable API login/logout

    # Optional JWT endpoints
    # path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    # path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
