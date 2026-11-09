from copy import deepcopy
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from openpyxl import load_workbook
from rest_framework.test import APITestCase

from .models import Choice, Page, Question, Vote, Voting

User = get_user_model()
PASSWORD = 'Mountain-River-27!'


def survey_payload():
    return {
        'title': 'Опрос', 'description': 'Описание',
        'pages': [{
            'title': 'Страница', 'order': 0,
            'questions': [{
                'title': 'Вопрос', 'type': 'checkbox',
                'choices': [{'name': 'Да'}, {'name': 'Нет'}],
            }],
        }],
    }


class VotingAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user(username='author', password=PASSWORD)
        cls.participant = User.objects.create_user(username='participant', password=PASSWORD)
        cls.voting = Voting.objects.create(author=cls.author, title='Опрос', description='Описание')
        cls.page = Page.objects.create(voting=cls.voting, title='Страница')
        cls.question = Question.objects.create(page=cls.page, title='Вопрос')
        cls.choice = Choice.objects.create(question=cls.question, name='Да')
        cls.other_choice = Choice.objects.create(question=cls.question, name='Нет')
        cls.foreign_voting = Voting.objects.create(author=cls.participant, title='Чужой', description='Описание')
        page = Page.objects.create(voting=cls.foreign_voting, title='Чужая страница')
        cls.foreign_question = Question.objects.create(page=page, title='Чужой вопрос')
        cls.foreign_choice = Choice.objects.create(question=cls.foreign_question, name='Другой вариант')

    def setUp(self):
        self.client.force_authenticate(self.author)
        self.detail_url = reverse('voting-detail', args=[self.voting.pk])
        self.submission_url = reverse('submission-create', args=[self.voting.pk])

    def publish(self):
        response = self.client.post(reverse('voting-publish', args=[self.voting.pk]))
        self.assertEqual(response.status_code, 200, response.data)

    def answers(self):
        return {'answers': [{'question': self.question.pk, 'choice': self.choice.pk}]}

    def test_create_assigns_author_and_creates_draft(self):
        payload = survey_payload()
        payload.update(author=self.participant.pk, is_submit=True)
        response = self.client.post(reverse('voting-list'), payload, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        voting = Voting.objects.get(pk=response.data['id'])
        self.assertEqual(voting.author, self.author)
        self.assertFalse(voting.is_submit)
        self.assertEqual(Choice.objects.filter(question__page__voting=voting).count(), 2)

    def test_list_contains_only_own_surveys(self):
        response = self.client.get(reverse('voting-list'))
        self.assertEqual([row['id'] for row in response.data['results']], [self.voting.pk])

    def test_foreign_surveys_inaccessible_for_all_owner_actions(self):
        self.client.force_authenticate(self.participant)
        cases = [('voting-detail', 'get'), ('voting-detail', 'patch'), ('voting-detail', 'put'),
                 ('voting-detail', 'delete'), ('voting-publish', 'post'), ('voting-unpublish', 'post'),
                 ('voting-statistics', 'get'), ('voting-responses', 'get'),
                 ('voting-export-json', 'get'), ('voting-export-votes', 'get')]
        for route, method in cases:
            with self.subTest(route=route, method=method):
                response = getattr(self.client, method)(reverse(route, args=[self.voting.pk]))
                self.assertEqual(response.status_code, 404)
        self.assertTrue(Voting.objects.filter(pk=self.voting.pk).exists())

    def test_anonymous_cannot_manage_or_submit(self):
        self.client.force_authenticate(None)
        for route, method, args in [
            ('voting-list', 'get', []), ('voting-list', 'post', []),
            ('voting-detail', 'patch', [self.voting.pk]),
            ('voting-detail', 'delete', [self.voting.pk]),
            ('voting-publish', 'post', [self.voting.pk]),
            ('voting-statistics', 'get', [self.voting.pk]),
            ('voting-export-json', 'get', [self.voting.pk]),
            ('voting-export-votes', 'get', [self.voting.pk]),
            ('submission-create', 'post', [self.voting.pk]),
        ]:
            with self.subTest(route=route, method=method):
                self.assertEqual(getattr(self.client, method)(reverse(route, args=args)).status_code, 401)

    def test_patch_metadata_preserves_entire_tree_and_votes(self):
        vote = Vote.objects.create(user=self.participant, question=self.question, choice=self.choice)
        response = self.client.patch(self.detail_url, {'title': 'Новое название'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.voting.refresh_from_db()
        self.assertEqual(self.voting.title, 'Новое название')
        vote.refresh_from_db()
        self.assertEqual(vote.choice_id, self.choice.pk)
        self.assertTrue(Page.objects.filter(pk=self.page.pk).exists())
        self.assertTrue(Question.objects.filter(pk=self.question.pk).exists())

    def test_draft_tree_update_retains_ids(self):
        payload = self.client.get(self.detail_url).data
        payload['pages'][0]['questions'][0]['choices'][0]['name'] = 'Обновлённый вариант'
        response = self.client.put(self.detail_url, payload, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.choice.refresh_from_db()
        self.assertEqual(self.choice.name, 'Обновлённый вариант')
        self.assertEqual(response.data['pages'][0]['id'], self.page.pk)
        self.assertEqual(response.data['pages'][0]['questions'][0]['id'], self.question.pk)

    def test_invalid_tree_update_rolls_back_metadata_and_nested_writes(self):
        original = deepcopy(self.client.get(self.detail_url).data)
        payload = deepcopy(original)
        payload['title'] = 'Не сохранять'
        payload['pages'][0]['title'] = 'Тоже не сохранять'
        payload['pages'][0]['questions'][0]['choices'][1]['id'] = self.foreign_choice.pk
        response = self.client.patch(self.detail_url, payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get(self.detail_url).data, original)

    def test_partial_nested_payload_is_rejected_without_changes(self):
        response = self.client.patch(self.detail_url, {'pages': [{'id': self.page.pk}]}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertTrue(Page.objects.filter(pk=self.page.pk).exists())

    def test_create_failure_rolls_back_all_nested_rows(self):
        counts = [model.objects.count() for model in (Voting, Page, Question, Choice)]
        with patch('surApp.services.validate_logic', side_effect=RuntimeError('simulated failure')):
            with self.assertRaises(RuntimeError):
                self.client.post(reverse('voting-list'), survey_payload(), format='json')
        self.assertEqual([model.objects.count() for model in (Voting, Page, Question, Choice)], counts)

    def test_published_structure_is_locked(self):
        self.publish()
        response = self.client.patch(self.detail_url, {'pages': survey_payload()['pages']}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertTrue(Choice.objects.filter(pk=self.choice.pk).exists())

    def test_unpublished_survey_with_votes_still_has_locked_structure(self):
        self.publish()
        Vote.objects.create(user=self.participant, question=self.question, choice=self.choice)
        self.client.post(reverse('voting-unpublish', args=[self.voting.pk]))
        response = self.client.patch(self.detail_url, {'pages': []}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Vote.objects.count(), 1)

    def test_empty_survey_cannot_be_published(self):
        self.voting.pages.all().delete()
        response = self.client.post(reverse('voting-publish', args=[self.voting.pk]))
        self.assertEqual(response.status_code, 400)
        self.voting.refresh_from_db()
        self.assertFalse(self.voting.is_submit)

    def test_public_endpoint_only_exposes_published_surveys(self):
        url = reverse('public-voting-detail', args=[self.voting.pk])
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_authenticate(self.author)
        self.publish()
        self.client.force_authenticate(None)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('author', response.data)

    def test_pages_ordered_by_order_then_id(self):
        earlier = Page.objects.create(voting=self.voting, title='Первая', order=0)
        self.page.order = 10
        self.page.save()
        self.assertEqual([p['id'] for p in self.client.get(self.detail_url).data['pages']], [earlier.pk, self.page.pk])

    def test_logic_references_are_validated(self):
        valid = {'question_answer_pairs': f'[[{self.question.pk}, {self.choice.pk}]]',
                 'hidden_pages': f'[[{self.page.pk}]]'}
        self.assertEqual(self.client.patch(self.detail_url, valid, format='json').status_code, 200)
        for payload in [{'hidden_pages': 'not json'}, {'hidden_pages': '[]'},
                        {'question_answer_pairs': f'[[{self.question.pk}, {self.foreign_choice.pk}]]'}]:
            with self.subTest(payload=payload):
                self.assertEqual(self.client.patch(self.detail_url, payload, format='json').status_code, 400)
        self.voting.refresh_from_db()
        self.assertEqual(self.voting.hidden_pages, valid['hidden_pages'])

    def test_answer_submission_and_repeat_rejection(self):
        self.publish()
        self.client.force_authenticate(self.participant)
        payload = self.answers()
        payload['answers'].append({'question': self.question.pk, 'choice': self.other_choice.pk})
        response = self.client.post(self.submission_url, payload, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(set(Vote.objects.values_list('user_id', flat=True)), {self.participant.pk})
        self.assertEqual(self.client.post(self.submission_url, payload, format='json').status_code, 400)
        self.assertEqual(Vote.objects.count(), 2)

    def test_draft_rejects_answers(self):
        self.assertEqual(self.client.post(self.submission_url, self.answers(), format='json').status_code, 404)
        self.assertFalse(Vote.objects.exists())

    def test_bad_answers_do_not_create_any_votes(self):
        self.publish()
        for bad in [
            {'question': self.question.pk, 'choice': self.foreign_choice.pk},
            {'question': self.foreign_question.pk, 'choice': self.foreign_choice.pk},
            {'question': 999999, 'choice': self.choice.pk},
            {'question': self.question.pk, 'choice': self.choice.pk, 'user': self.participant.pk},
            {'question': self.question.pk, 'choice': self.choice.pk},  # duplicate
        ]:
            with self.subTest(answer=bad):
                payload = self.answers()
                payload['answers'].append(bad)
                self.assertEqual(self.client.post(self.submission_url, payload, format='json').status_code, 400)
                self.assertFalse(Vote.objects.exists())
        self.assertEqual(self.client.post(self.submission_url, {'answers': []}, format='json').status_code, 400)

    def test_radio_rejects_multiple_choices(self):
        self.question.type = 'radio'
        self.question.save()
        self.publish()
        payload = self.answers()
        payload['answers'].append({'question': self.question.pk, 'choice': self.other_choice.pk})
        self.assertEqual(self.client.post(self.submission_url, payload, format='json').status_code, 400)
        self.assertFalse(Vote.objects.exists())

    def test_statistics_and_exports(self):
        self.choice.name = '=1+1'
        self.choice.save()
        Vote.objects.create(user=self.participant, question=self.question, choice=self.choice)
        response = self.client.get(reverse('voting-statistics', args=[self.voting.pk]))
        self.assertEqual([c['votes_count'] for c in response.data[0]['choices']], [1, 0])
        response = self.client.get(reverse('voting-responses', args=[self.voting.pk]))
        self.assertEqual(response.data['count'], 1)
        response = self.client.get(reverse('voting-export-json', args=[self.voting.pk]))
        self.assertEqual(response.json()['id'], self.voting.pk)
        response = self.client.get(reverse('voting-export-votes', args=[self.voting.pk]))
        workbook = load_workbook(BytesIO(response.content))
        self.assertEqual(workbook.active['E2'].value, '=1+1')
        self.assertEqual(workbook.active['E2'].data_type, 's')
        workbook.close()

    def test_owner_can_delete_survey(self):
        self.assertEqual(self.client.delete(self.detail_url).status_code, 204)
        self.assertFalse(Voting.objects.filter(pk=self.voting.pk).exists())


class AuthenticationAPITests(APITestCase):
    def test_register_login_refresh_and_logout(self):
        response = self.client.post(reverse('register'), {
            'username': 'new-user', 'email': 'user@example.com', 'password': PASSWORD,
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertNotIn('password', response.data)
        self.assertTrue(User.objects.get(username='new-user').check_password(PASSWORD))
        response = self.client.post(reverse('login'), {'username': 'new-user', 'password': PASSWORD}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        tokens = response.data
        response = self.client.post(reverse('token-refresh'), {'refresh': tokens['refresh']}, format='json')
        self.assertEqual(response.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        self.assertEqual(self.client.get(reverse('token-validate')).status_code, 200)
        self.assertEqual(self.client.post(reverse('logout'), {'refresh': tokens['refresh']}, format='json').status_code, 204)
        self.client.credentials()
        self.assertEqual(self.client.post(reverse('token-refresh'), {'refresh': tokens['refresh']}, format='json').status_code, 401)

    def test_registration_rejects_weak_password(self):
        response = self.client.post(reverse('register'), {'username': 'weak', 'password': '123'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(username='weak').exists())

    def test_validation_requires_token_and_bad_login_fails(self):
        self.assertEqual(self.client.get(reverse('token-validate')).status_code, 401)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid')
        self.assertEqual(self.client.get(reverse('token-validate')).status_code, 401)
        self.client.credentials()
        response = self.client.post(reverse('login'), {'username': 'missing', 'password': PASSWORD}, format='json')
        self.assertEqual(response.status_code, 401)

    def test_cannot_logout_another_user(self):
        author = User.objects.create_user(username='owner', password=PASSWORD)
        User.objects.create_user(username='other', password=PASSWORD)
        tokens = self.client.post(reverse('login'), {'username': 'other', 'password': PASSWORD}, format='json').data
        self.client.force_authenticate(author)
        self.assertEqual(self.client.post(reverse('logout'), {'refresh': tokens['refresh']}, format='json').status_code, 400)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post(reverse('token-refresh'), {'refresh': tokens['refresh']}, format='json').status_code, 200)
