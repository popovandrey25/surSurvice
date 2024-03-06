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


class Question(models.Model):
    title = models.CharField(max_length=100)
    voting = models.ForeignKey(Voting, related_name='questions', on_delete=models.CASCADE)


class Choice(models.Model):
    name = models.CharField(max_length=150)
    question = models.ForeignKey(Question, related_name='choices', on_delete=models.CASCADE)


class Vote(models.Model):
    user = models.ForeignKey(User, related_name='votes', on_delete=models.CASCADE)
    choice = models.ForeignKey(Choice, related_name='votes', on_delete=models.CASCADE)
    question = models.ForeignKey(Question, related_name='votes', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.username}'s vote for {self.choice.name} in question: {self.question.title}"



# {
#     "title": "Название вашего голосования",
#     "description": "Описание вашего голосования",
#     "author": 1,
#     "questions": [
#         {
#             "title": "Вопрос 1",
#             "choices": [
#                 {"name": "Вариант ответа 1"},
#                 {"name": "Вариант ответа 2"}
#             ]
#         },
#         {
#             "title": "Вопрос 2",
#             "choices": [
#                 {"name": "Вариант ответа 1"},
#                 {"name": "Вариант ответа 2"},
#                 {"name": "Вариант ответа 3"}
#             ]
#         }
#     ]
# }
