import json

from django.db.models import Count, Prefetch
from django.http import HttpResponse
from openpyxl import Workbook
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .models import Choice, Question, Vote
from .permissions import IsVotingAuthor
from .serializers import (
    PublicVotingSerializer, SubmissionSerializer, VoteSerializer, VotingSerializer,
)
from .services import delete_voting, set_publication, submit_votes, voting_queryset


class VotingViewSet(ModelViewSet):
    """Author-only management API. Participant endpoints are separate."""

    serializer_class = VotingSerializer
    permission_classes = [IsAuthenticated, IsVotingAuthor]

    def get_queryset(self):
        return voting_queryset().filter(author=self.request.user)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_destroy(self, instance):
        delete_voting(voting_id=instance.pk)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        voting = set_publication(voting_id=self.get_object().pk, published=True)
        return Response(self.get_serializer(voting).data)

    @action(detail=True, methods=['post'])
    def unpublish(self, request, pk=None):
        voting = set_publication(voting_id=self.get_object().pk, published=False)
        return Response(self.get_serializer(voting).data)

    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        voting = self.get_object()
        questions = Question.objects.filter(page__voting=voting).order_by('page__order', 'page_id', 'id').prefetch_related(
            Prefetch('choices', queryset=Choice.objects.annotate(votes_count=Count('votes')).order_by('id'))
        )
        return Response([
            {
                'question_id': question.pk,
                'question_title': question.title,
                'question_type': question.type,
                'choices': [
                    {'choice_id': choice.pk, 'choice_title': choice.name, 'votes_count': choice.votes_count}
                    for choice in question.choices.all()
                ],
            }
            for question in questions
        ])

    @action(detail=True, methods=['get'])
    def responses(self, request, pk=None):
        voting = self.get_object()
        votes = Vote.objects.filter(question__page__voting=voting).order_by('id')
        page = self.paginate_queryset(votes)
        return self.get_paginated_response(VoteSerializer(page, many=True).data)

    @action(detail=True, methods=['get'], url_path='export-json')
    def export_json(self, request, pk=None):
        voting = self.get_object()
        response = HttpResponse(
            json.dumps(self.get_serializer(voting).data, ensure_ascii=False, indent=2),
            content_type='application/json',
        )
        response['Content-Disposition'] = f'attachment; filename="voting_{voting.pk}.json"'
        return response

    @action(detail=True, methods=['get'], url_path='export-votes')
    def export_votes(self, request, pk=None):
        voting = self.get_object()
        votes = Vote.objects.filter(question__page__voting=voting).select_related('user', 'question', 'choice').order_by('id')
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = 'Votes'
        sheet.append(['User', 'Question ID', 'Question', 'Choice ID', 'Choice'])
        for vote in votes:
            sheet.append([vote.user.username, vote.question_id, vote.question.title, vote.choice_id, vote.choice.name])
            # User-authored text must remain text, including strings starting '='.
            for column in (1, 3, 5):
                sheet.cell(row=sheet.max_row, column=column).data_type = 's'
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="votes_voting_{voting.pk}.xlsx"'
        workbook.save(response)
        workbook.close()
        return response


class PublicVotingDetailView(RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = PublicVotingSerializer

    def get_queryset(self):
        return voting_queryset().filter(is_submit=True)


class SubmissionCreateView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SubmissionSerializer

    def post(self, request, pk):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        votes = submit_votes(voting_id=pk, user=request.user, answers=serializer.validated_data['answers'])
        return Response(VoteSerializer(votes, many=True).data, status=status.HTTP_201_CREATED)
