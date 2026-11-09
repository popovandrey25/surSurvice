"""Transactional operations on a survey and its nested content."""

import json

from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from .models import Choice, Page, Question, Vote, Voting


def voting_queryset():
    return Voting.objects.order_by('id').prefetch_related(
        Prefetch('pages', queryset=Page.objects.order_by('order', 'id').prefetch_related(
            Prefetch('questions', queryset=Question.objects.order_by('id').prefetch_related(
                Prefetch('choices', queryset=Choice.objects.order_by('id'))
            ))
        ))
    )


def _sync_children(manager, items, child_field=None):
    """A supplied list replaces a collection; IDs retain existing objects."""
    existing = {obj.pk: obj for obj in manager.all()}
    retained = set()
    for item in items:
        data = item.copy()
        pk = data.pop('id', None)
        children = data.pop(child_field) if child_field else None
        if pk is not None:
            if pk not in existing or pk in retained:
                raise ValidationError({'pages': 'ID повторяется или не принадлежит родительскому объекту.'})
            obj = existing[pk]
            for field, value in data.items():
                setattr(obj, field, value)
            obj.save()
        else:
            obj = manager.create(**data)
        retained.add(obj.pk)
        if child_field:
            next_field = 'choices' if child_field == 'questions' else None
            _sync_children(getattr(obj, child_field), children, next_field)
    manager.exclude(pk__in=retained).delete()


def validate_logic(voting):
    """Keep the legacy JSON-string format, but validate all references."""
    try:
        pairs = json.loads(voting.question_answer_pairs or '[]')
        hidden = json.loads(voting.hidden_pages or '[]')
    except (TypeError, ValueError):
        raise ValidationError({'logic': 'Правила должны содержать корректный JSON.'})
    if not isinstance(pairs, list) or not isinstance(hidden, list) or len(pairs) != len(hidden):
        raise ValidationError({'logic': 'Условия и списки скрываемых страниц должны иметь одинаковую длину.'})
    page_ids = set(voting.pages.values_list('id', flat=True))
    choice_questions = dict(Choice.objects.filter(question__page__voting=voting).values_list('id', 'question_id'))
    for pair, pages in zip(pairs, hidden):
        if (
            not isinstance(pair, list) or len(pair) != 2
            or any(type(value) is not int for value in pair)
            or choice_questions.get(pair[1]) != pair[0]
            or not isinstance(pages, list)
            or any(type(pk) is not int or pk not in page_ids for pk in pages)
        ):
            raise ValidationError({'logic': 'Условие или скрываемая страница не принадлежат этому опросу.'})


@transaction.atomic
def create_voting(*, author, data):
    data = data.copy()
    pages = data.pop('pages')
    voting = Voting.objects.create(author=author, **data)
    _sync_children(voting.pages, pages, 'questions')
    validate_logic(voting)
    return voting_queryset().get(pk=voting.pk)


@transaction.atomic
def update_voting(*, voting_id, data):
    voting = Voting.objects.select_for_update().get(pk=voting_id)
    data = data.copy()
    pages = data.pop('pages', None)
    structure_changed = pages is not None or any(
        field in data and data[field] != getattr(voting, field)
        for field in ('question_answer_pairs', 'hidden_pages')
    )
    if structure_changed and (
        voting.is_submit or Vote.objects.filter(question__page__voting=voting).exists()
    ):
        raise ValidationError({'pages': 'Структуру можно менять только в черновике без ответов.'})
    for field, value in data.items():
        setattr(voting, field, value)
    voting.save()
    if pages is not None:
        _sync_children(voting.pages, pages, 'questions')
    validate_logic(voting)
    return voting_queryset().get(pk=voting.pk)


@transaction.atomic
def set_publication(*, voting_id, published):
    voting = Voting.objects.select_for_update().get(pk=voting_id)
    if published:
        pages = voting.pages.prefetch_related('questions__choices')
        if not pages or any(not page.questions.all() for page in pages):
            raise ValidationError({'pages': 'Для публикации нужны страницы с вопросами.'})
        for page in pages:
            for question in page.questions.all():
                if question.type not in ('checkbox', 'radio') or not question.choices.all():
                    raise ValidationError({'pages': 'Каждому вопросу нужны поддерживаемый тип и варианты ответа.'})
        validate_logic(voting)
    voting.is_submit = published
    voting.save(update_fields=['is_submit'])
    return voting_queryset().get(pk=voting.pk)


@transaction.atomic
def delete_voting(*, voting_id):
    voting = Voting.objects.select_for_update().get(pk=voting_id)
    voting.delete()


@transaction.atomic
def submit_votes(*, voting_id, user, answers):
    # The same survey lock also serializes editing, publication and submissions
    # on databases with row-level locking (e.g. PostgreSQL).
    voting = get_object_or_404(Voting.objects.select_for_update(), pk=voting_id, is_submit=True)
    if Vote.objects.filter(user=user, question__page__voting=voting).exists():
        raise ValidationError({'answers': 'Вы уже ответили на этот опрос.'})
    questions = {q.pk: q for q in Question.objects.filter(page__voting=voting)}
    choices = dict(Choice.objects.filter(question__page__voting=voting).values_list('id', 'question_id'))
    seen = set()
    answered = set()
    votes = []
    for answer in answers:
        question_id, choice_id = answer['question'], answer['choice']
        question = questions.get(question_id)
        if question is None or choices.get(choice_id) != question_id:
            raise ValidationError({'answers': 'Вопрос или вариант ответа не принадлежит этому опросу/вопросу.'})
        if (question_id, choice_id) in seen:
            raise ValidationError({'answers': 'Один вариант нельзя выбрать дважды.'})
        if question.type not in ('checkbox', 'radio'):
            raise ValidationError({'answers': 'Неподдерживаемый тип вопроса.'})
        if question.type == 'radio' and question_id in answered:
            raise ValidationError({'answers': 'Для radio можно выбрать только один вариант.'})
        seen.add((question_id, choice_id))
        answered.add(question_id)
        votes.append(Vote(user=user, question=question, choice_id=choice_id))
    return Vote.objects.bulk_create(votes)
