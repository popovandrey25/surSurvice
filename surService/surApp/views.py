from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import *
from rest_framework.permissions import IsAuthenticated
from .serializers import *
from rest_framework.generics import ListAPIView, CreateAPIView, RetrieveUpdateAPIView, DestroyAPIView
from django.http import Http404
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token


class HomeView(APIView):
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return Response({"message": f"Привет, {request.user.username}!"}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "Войти"}, status=status.HTTP_200_OK)


class UserSurveysView(ListAPIView):
    serializer_class = SurveySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        if user_id != self.request.user.id:
            raise Http404("Страница не найдена")
        return Survey.objects.filter(user_id=user_id)


class VotingListByUserAPIView(ListAPIView):
    serializer_class = VotingSerializer

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        return Voting.objects.filter(author=user_id)


class SurveyCreateAPIView(CreateAPIView):
    queryset = Survey.objects.all()
    serializer_class = SurveySerializer
    permission_classes = [IsAuthenticated]  # Убедитесь, что пользователь аутентифицирован, прежде чем создавать опросы

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class VotingCreateAPIView(CreateAPIView):
    queryset = Voting.objects.all()
    serializer_class = VotingSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class VotingUpdateAPIView(RetrieveUpdateAPIView):
    queryset = Voting.objects.all()
    serializer_class = VotingSerializer
    permission_classes = [IsAuthenticated,]

    def perform_update(self, serializer):
        # Проверяем, что текущий пользователь является автором опроса
        if serializer.instance.author != self.request.user:
            raise PermissionDenied("You do not have permission to perform this action.")
        serializer.save()

class VotingDeleteAPIView(DestroyAPIView):
    queryset = Voting.objects.all()
    serializer_class = VotingSerializer
    permission_classes = [IsAuthenticated]

    def perform_destroy(self, instance):
        # Проверяем, что текущий пользователь является автором опроса
        if instance.author != self.request.user:
            raise PermissionDenied("You do not have permission to delete this voting.")
        instance.delete()
