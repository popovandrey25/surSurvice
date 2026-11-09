from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .auth_views import LogoutView, UserLoginView, UserRegistrationView, ValidateTokenView

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('token/validate/', ValidateTokenView.as_view(), name='token-validate'),
]
