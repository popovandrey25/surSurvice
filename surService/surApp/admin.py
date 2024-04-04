from django.contrib import admin
from .models import *
from nested_inline.admin import NestedStackedInline, NestedModelAdmin


class ChoiceInline(NestedStackedInline):
    model = Choice
    extra = 1

class QuestionInline(NestedStackedInline):
    model = Question
    extra = 1
    inlines = [ChoiceInline]

class PageInline(NestedStackedInline):
    model = Page
    extra = 1
    inlines = [QuestionInline]

class VotingAdmin(NestedModelAdmin):
    model = Voting
    inlines = [PageInline]
    list_display = ['title', 'description', 'author']

admin.site.register(Voting, VotingAdmin)
admin.site.register(Vote)
