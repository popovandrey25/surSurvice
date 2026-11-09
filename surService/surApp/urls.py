from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PublicVotingDetailView, SubmissionCreateView, VotingViewSet

router = DefaultRouter()
router.register('votings', VotingViewSet, basename='voting')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('surApp.auth_urls')),
    path('public/votings/<int:pk>/', PublicVotingDetailView.as_view(), name='public-voting-detail'),
    path('public/votings/<int:pk>/submissions/', SubmissionCreateView.as_view(), name='submission-create'),
]
