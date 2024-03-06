from django.contrib import admin
from django.urls import path, include
from surApp.views import *


urlpatterns = [
    path('admin/', admin.site.urls),
    path('home/', HomeView.as_view(), name='home'),
    path('show_survey/<int:user_id>/', UserSurveysView.as_view(), name='user_surveys'),
    path('show_votings/<int:user_id>/', VotingListByUserAPIView.as_view(), name='voting-list-by-user'),
    path('home/drf-auth/', include('rest_framework.urls')),
    path('create/survey/', SurveyCreateAPIView.as_view(), name='survey-create'),
    path('create/voting/', VotingCreateAPIView.as_view(), name='voting-create'),
    path('update/voting/<int:pk>/', VotingUpdateAPIView.as_view(), name='voting-update'),
    path('delete/voting/<int:pk>/', VotingDeleteAPIView.as_view(), name='voting-delete'),
]
