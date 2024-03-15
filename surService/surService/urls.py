from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from surApp.views import *


urlpatterns = [
    path('admin/', admin.site.urls),
    path('home/', HomeView.as_view(), name='home'),
    path('show_votings/<int:user_id>/', VotingListByUserAPIView.as_view(), name='voting-list-by-user'),
    path('create/voting/', VotingCreateAPIView.as_view(), name='voting-create'),
    path('update/voting/<int:pk>/', VotingUpdateAPIView.as_view(), name='voting-update'),
    path('delete/voting/<int:pk>/', VotingDeleteAPIView.as_view(), name='voting-delete'),
    path('api/register/', UserRegistrationAPIView.as_view(), name='register'),
    path('api/login/', UserLoginAPIView.as_view(), name='login'),
    path('api/logout/', LogoutAPIView.as_view(), name='logout'),
]
