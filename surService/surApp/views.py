from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .models import *
from rest_framework.permissions import IsAuthenticated, AllowAny
from .serializers import *
from rest_framework.generics import ListAPIView, CreateAPIView, RetrieveUpdateAPIView, DestroyAPIView, GenericAPIView, \
    RetrieveAPIView
from django.http import Http404, JsonResponse


class HomeView(APIView):
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return Response({"message": f"Привет, {request.user.username}!"}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "Войти"}, status=status.HTTP_200_OK)


class VotingListByUserAPIView(ListAPIView):
    serializer_class = VotingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        if user_id != self.request.user.id:
            raise Http404("Страница не найдена")
        return Voting.objects.filter(author=user_id)


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


class UserRegistrationAPIView(CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class UserLoginAPIView(GenericAPIView):
    serializer_class = UserLoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        refresh = RefreshToken.for_user(user)

        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user_id': str(user.id),
        }, status=status.HTTP_200_OK)


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            # Получаем refresh token из запроса
            refresh_token = request.data.get('refresh_token')
            if not refresh_token:
                return Response({'error': 'Отсутствует refresh token'}, status=status.HTTP_400_BAD_REQUEST)

            # Удаление токена из черного списка
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response({'detail': 'Вы успешно вышли из учетной записи.'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class VoteBulkCreateView(CreateAPIView):
    queryset = Vote.objects.all()
    serializer_class = VoteSerializer

    def post(self, request, *args, **kwargs):
        voting_id = self.kwargs.get('pk')
        voting = get_object_or_404(Voting, pk=voting_id)
        questions = voting.questions.all()
        if not questions:
            return Response({"error": "No questions found for this voting"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        # question_ids = [item['question'].id for item in serializer.validated_data]
        # if set(question_ids) != set(questions.values_list('id', flat=True)):
        #     return Response({"error": "Not all questions belong to the specified voting"},
        #                         status=status.HTTP_400_BAD_REQUEST)

        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        serializer.save()


class DetailStatisticAPIView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = VoteSerializer
    queryset = Vote.objects.all()

    def get(self, request, *args, **kwargs):
        voting_id = self.kwargs.get('pk')
        votes = Vote.objects.filter(question__voting_id=voting_id)  # Получаем все голоса для определенного опроса
        serializer = self.get_serializer(votes, many=True)
        return Response(serializer.data)
