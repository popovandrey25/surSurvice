from django.db import models
from django.contrib.auth.models import User

class Survey(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    # Другие поля для общей информации о тестировании, голосовании и анкетировании
    class Meta:
        verbose_name = "Опрос"
        verbose_name_plural = "Опросы"


class Voting(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    is_submit = models.BooleanField(default=False)
    question_answer_pairs = models.TextField(blank=True)
    hidden_pages = models.TextField(blank=True)

class Page(models.Model):
    voting = models.ForeignKey(Voting, related_name='pages', on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    order = models.IntegerField(default=0)

class Question(models.Model):
    title = models.CharField(max_length=100)
    type = models.CharField(max_length=50, default='checkbox')
    page = models.ForeignKey(Page, related_name='questions', on_delete=models.CASCADE)

class Choice(models.Model):
    name = models.CharField(max_length=150)
    question = models.ForeignKey(Question, related_name='choices', on_delete=models.CASCADE)


class Vote(models.Model):
    user = models.ForeignKey(User, related_name='votes', on_delete=models.CASCADE)
    choice = models.ForeignKey(Choice, related_name='votes', on_delete=models.CASCADE)
    question = models.ForeignKey(Question, related_name='votes', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.username}'s vote for {self.choice.name} in question: {self.question.title}"


# Пример запроса POST для создания опроса
# {
#     "title": "Название опросаИЗМ",
#     "description": "Описание опроса",
#     "author": 1,
#     "pages": [
#         {
#             "title": "Заголовок страницы 1ИЗМ",
#             "questions": [
#                 {
#                     "title": "Вопрос 1 на странице 1ИЗМ",
#                     "type": "checkbox",
#                     "choices": [
#                         {
#                             "name": "Вариант ответа 1ИЗМ"
#                         },
#                         {
#                             "name": "Вариант ответа 2"
#                         }
#                     ]
#                 },
#                 {
#                     "title": "Вопрос 2 на странице 1",
#                     "type": "checkbox",
#                     "choices": [
#                         {
#                             "name": "Вариант ответа 1"
#                         },
#                         {
#                             "name": "Вариант ответа 2"
#                         }
#                     ]
#                 }
#             ]
#         },
#         {
#             "title": "Заголовок страницы 2",
#             "questions": [
#                 {
#                     "title": "Вопрос 1 на странице 2",
#                     "type": "checkbox",
#                     "choices": [
#                         {
#                             "name": "Вариант ответа 1"
#                         },
#                         {
#                             "name": "Вариант ответа 2"
#                         }
#                     ]
#                 },
#                 {
#                     "title": "Вопрос 2 на странице 2",
#                     "type": "checkbox",
#                     "choices": [
#                         {
#                             "name": "Вариант ответа 1"
#                         },
#                         {
#                             "name": "Вариант ответа 2"
#                         }
#                     ]
#                 }
#             ]
#         }
#     ]
# }

# Пример отправки варианта ответа
# [
#     {"user": 1, "question": 86, "choice": 190},
#     {"user": 1, "question": 87, "choice": 192}
# ]

# Пример добавления логики (PATCH)
# {
#     "question_answer_pairs": "[[1, 2], [2, 3], [3, 1]]",
#     "hidden_pages": "[[2], [3, 4], [3, 4]]"
# }
