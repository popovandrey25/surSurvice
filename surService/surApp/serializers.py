from django.contrib.auth import authenticate
from rest_framework import serializers
from .models import *


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'name']

    def create(self, validated_data):
        question = self.context['question']
        return Choice.objects.create(question=question, **validated_data)

class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True)

    class Meta:
        model = Question
        fields = ['id', 'title', 'type', 'choices']

    def create(self, validated_data):
        choices_data = validated_data.pop('choices')
        question = Question.objects.create(**validated_data)
        for choice_data in choices_data:
            Choice.objects.create(question=question, **choice_data)
        return question

class PageSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True)

    class Meta:
        model = Page
        fields = ['id', 'order', 'title', 'questions']

    def create(self, validated_data):
        questions_data = validated_data.pop('questions')
        page = Page.objects.create(**validated_data)
        for question_data in questions_data:
            choices_data = question_data.pop('choices', [])
            question = Question.objects.create(page=page, **question_data)
            for choice_data in choices_data:
                Choice.objects.create(question=question, **choice_data)
        return page

class VotingSerializer(serializers.ModelSerializer):
    author = serializers.PrimaryKeyRelatedField(read_only=True)
    pages = PageSerializer(many=True)

    class Meta:
        model = Voting
        fields = ['id', 'title', 'description', 'author', 'is_submit', 'question_answer_pairs', 'hidden_pages', 'pages']

    def create(self, validated_data):
        pages_data = validated_data.pop('pages')
        voting = Voting.objects.create(**validated_data)
        for page_data in pages_data:
            questions_data = page_data.pop('questions', [])
            page = Page.objects.create(voting=voting, **page_data)
            for question_data in questions_data:
                choices_data = question_data.pop('choices', [])
                question = Question.objects.create(page=page, **question_data)
                for choice_data in choices_data:
                    Choice.objects.create(question=question, **choice_data)
        return voting

    def update(self, instance, validated_data):
        pages_data = validated_data.pop('pages', [])
        instance = super().update(instance, validated_data)
        instance.pages.all().delete()  # Удаляем все старые страницы
        for page_data in pages_data:
            questions_data = page_data.pop('questions', [])
            page = Page.objects.create(voting=instance, **page_data)
            for question_data in questions_data:
                choices_data = question_data.pop('choices', [])
                question = Question.objects.create(page=page, **question_data)
                for choice_data in choices_data:
                    Choice.objects.create(question=question, **choice_data)
        return instance


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        user = authenticate(**data)
        if user and user.is_active:
            return user
        raise serializers.ValidationError("Неверные учетные данные")


class VoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vote
        fields = ['user', 'question', 'choice']

class BulkVoteSerializer(serializers.ListSerializer):
    child = VoteSerializer()

    def create(self, validated_data):
        votes = [Vote(**item) for item in validated_data]
        return Vote.objects.bulk_create(votes)
