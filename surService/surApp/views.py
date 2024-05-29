import io
import pandas as pd
import json
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .models import *
from rest_framework.permissions import IsAuthenticated, AllowAny
from .serializers import *
from rest_framework.generics import ListAPIView, CreateAPIView, RetrieveUpdateAPIView, DestroyAPIView, GenericAPIView, \
    RetrieveAPIView, UpdateAPIView
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


class VotingDetailView(RetrieveAPIView):
    serializer_class = VotingSerializer
    queryset = Voting.objects.all()

    def get_object(self):
        voting_id = self.kwargs.get('pk')
        return get_object_or_404(self.get_queryset(), pk=voting_id)

    def get(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class VoteBulkCreateView(CreateAPIView):
    queryset = Voting.objects.all()
    serializer_class = VoteSerializer

    def post(self, request, *args, **kwargs):
        voting_id = self.kwargs.get('pk')
        voting = get_object_or_404(Voting, pk=voting_id)
        pages = voting.pages.all()
        if not pages:
            return Response({"error": "No pages found for this voting"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        # Проверяем, принадлежат ли все вопросы к определенным страницам опроса
        for vote_data in serializer.validated_data:
            question_id = vote_data['question']
            question = get_object_or_404(Question, pk=question_id.id)
            if question.page.voting != voting:
                return Response({"error": "Question does not belong to the specified voting"},
                                status=status.HTTP_400_BAD_REQUEST)

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
        votes = Vote.objects.filter(question__page__voting_id=voting_id)  # Фильтруем по идентификатору опроса
        serializer = self.get_serializer(votes, many=True)
        return Response(serializer.data)


class PollDetailAPIView(APIView):
    def get(self, request, poll_id, format=None):
        questions = Question.objects.filter(page__voting_id=poll_id)
        data = []
        for question in questions:
            question_data = {
                'question_id': question.id,
                'question_title': question.title,
                'question_type': question.type,
                'choices': []
            }
            choices = Choice.objects.filter(question_id=question.id)
            for choice in choices:
                votes_count = Vote.objects.filter(choice_id=choice.id).count()
                choice_data = {
                    'choice_id': choice.id,
                    'choice_title': choice.name,
                    'votes_count': votes_count
                }
                question_data['choices'].append(choice_data)
            data.append(question_data)
        return Response(data)


class VotingUpdateLogicView(UpdateAPIView):
    queryset = Voting.objects.all()
    serializer_class = VotingSerializer
    lookup_field = 'pk'  # или какой-то другой атрибут, используемый для идентификации объекта Voting

    # Переопределение метода partial_update для обновления только указанных полей
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()  # Получаем объект Voting для обновления
        # Обновляем только указанные поля, если они присутствуют в запросе
        if 'question_answer_pairs' in request.data:
            instance.question_answer_pairs = request.data['question_answer_pairs']
        if 'hidden_pages' in request.data:
            instance.hidden_pages = request.data['hidden_pages']
        # Сохраняем изменения
        instance.save()
        # Возвращаем успешный ответ
        return Response(self.get_serializer(instance).data, status=status.HTTP_200_OK)


class VotingUpdateSubmitView(UpdateAPIView):
    queryset = Voting.objects.all()
    serializer_class = VotingSerializer
    lookup_field = 'pk'  # или какой-то другой атрибут, используемый для идентификации объекта Voting

    # Переопределение метода partial_update для обновления только указанных полей
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()  # Получаем объект Voting для обновления
        # Обновляем только указанные поля, если они присутствуют в запросе
        if 'is_submit' in request.data:
            instance.is_submit = request.data['is_submit']
        instance.save()
        # Возвращаем успешный ответ
        return Response(self.get_serializer(instance).data, status=status.HTTP_200_OK)


class ValidateTokenView(APIView):

    def get(self, request):
        return Response({'detail': 'Token is valid.'})


class ExportVotesToExcelView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, voting_id, *args, **kwargs):
        voting = get_object_or_404(Voting, id=voting_id)
        votes = Vote.objects.filter(question__page__voting_id=voting_id).select_related('question', 'choice', 'user')

        # Собираем данные для экспорта
        data = []
        for vote in votes:
            data.append({
                'User': vote.user.username,
                'Question ID': vote.question.id,
                'Question': vote.question.title,
                'Choice ID': vote.choice.id,
                'Choice': vote.choice.name,
            })

        # Преобразуем данные в DataFrame
        df = pd.DataFrame(data)

        # Создаем Excel файл в памяти
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename=votes_voting_{voting_id}.xlsx'

        # Записываем DataFrame в Excel файл
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Votes')

        return response


class ExportVotingToJsonFileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, voting_id, *args, **kwargs):
        # Проверка существования опроса
        voting = get_object_or_404(Voting, id=voting_id)

        # Используем сериализатор для сериализации данных
        serializer = VotingSerializer(voting)
        data = serializer.data

        # Создание JSON-строки
        json_data = json.dumps(data, ensure_ascii=False, indent=4)

        # Создание буфера для файла
        buffer = io.BytesIO()
        buffer.write(json_data.encode('utf-8'))
        buffer.seek(0)

        # Создание HTTP-ответа с файлом для скачивания
        response = HttpResponse(buffer, content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="voting_{voting_id}.json"'
        return response
