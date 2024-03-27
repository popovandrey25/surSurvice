from django.contrib import admin
from .models import *

class SurveyAdmin(admin.ModelAdmin):
    list_display = ('title', 'user')


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1

class VotingAdmin(admin.ModelAdmin):
    inlines = [QuestionInline,]


# class ChoiceInline(admin.TabularInline):  # или StackedInline, в зависимости от предпочтений дизайна
#     model = Choice
#     extra = 1  # количество дополнительных форм для добавления выбора

# class QuestionInline(admin.TabularInline):
#     model = Question
#     extra = 1  # количество дополнительных форм для добавления вопроса
#
# class VotingAdmin(admin.ModelAdmin):
#     inlines = [QuestionInline, ]
#
#
# class VoteAdmin(admin.ModelAdmin):
#     pass

# Зарегистрируйте модель с кастомизированным админским классом
admin.site.register(Survey, SurveyAdmin)
admin.site.register(Voting, VotingAdmin)
admin.site.register(Vote)
# admin.site.register(Voting, VotingAdmin)
# admin.site.register(Vote, VoteAdmin)
