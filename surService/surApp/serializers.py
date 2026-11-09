import json

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Choice, Page, Question, Vote, Voting
from .services import create_voting, update_voting

User = get_user_model()


class ChoiceSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False, min_value=1)

    class Meta:
        model = Choice
        fields = ['id', 'name']


class QuestionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False, min_value=1)
    type = serializers.ChoiceField(choices=['checkbox', 'radio'], default='checkbox')
    choices = ChoiceSerializer(many=True, allow_empty=False)

    class Meta:
        model = Question
        fields = ['id', 'title', 'type', 'choices']


class PageSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False, min_value=1)
    order = serializers.IntegerField(min_value=0, default=0)
    questions = QuestionSerializer(many=True)

    class Meta:
        model = Page
        fields = ['id', 'order', 'title', 'questions']


class VotingSerializer(serializers.ModelSerializer):
    pages = PageSerializer(many=True)

    class Meta:
        model = Voting
        fields = ['id', 'title', 'description', 'author', 'is_submit',
                  'question_answer_pairs', 'hidden_pages', 'pages']
        read_only_fields = ['author', 'is_submit']

    def validate_pages(self, value):
        # PATCH may omit pages, but a supplied tree must be complete, even though
        # DRF otherwise propagates partial=True into its nested serializers.
        serializer = PageSerializer(data=value, many=True)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    def validate(self, attrs):
        for field in ('question_answer_pairs', 'hidden_pages'):
            if field in attrs:
                try:
                    value = json.loads(attrs[field] or '[]')
                except ValueError:
                    raise serializers.ValidationError({field: 'Ожидается JSON-массив.'})
                if not isinstance(value, list):
                    raise serializers.ValidationError({field: 'Ожидается JSON-массив.'})
        return attrs

    def create(self, validated_data):
        data = validated_data.copy()
        return create_voting(author=data.pop('author'), data=data)

    def update(self, instance, validated_data):
        return update_voting(voting_id=instance.pk, data=validated_data)


class PublicVotingSerializer(serializers.ModelSerializer):
    pages = PageSerializer(many=True, read_only=True)

    class Meta:
        model = Voting
        fields = ['id', 'title', 'description', 'question_answer_pairs', 'hidden_pages', 'pages']


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']
        read_only_fields = ['id']
        extra_kwargs = {'password': {'write_only': True, 'trim_whitespace': False}}

    def validate(self, attrs):
        user = User(username=attrs['username'], email=attrs.get('email', ''))
        try:
            validate_password(attrs['password'], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'password': exc.messages})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserLoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['user_id'] = self.user.pk
        return data


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class AnswerSerializer(serializers.Serializer):
    question = serializers.IntegerField(min_value=1)
    choice = serializers.IntegerField(min_value=1)

    def to_internal_value(self, data):
        if isinstance(data, dict) and 'user' in data:
            raise serializers.ValidationError({'user': 'Пользователь определяется по авторизации.'})
        return super().to_internal_value(data)


class SubmissionSerializer(serializers.Serializer):
    answers = AnswerSerializer(many=True, allow_empty=False)


class VoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vote
        fields = ['id', 'user', 'question', 'choice']
        read_only_fields = fields
