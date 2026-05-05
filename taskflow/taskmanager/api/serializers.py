from rest_framework import serializers
from django.contrib.auth import get_user_model
from projects.models import Project, ProjectMember, Sprint
from tasks.models import Task, Tag, Comment

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'name', 'email', 'role', 'is_premium', 'base_theme', 'color_theme')
        read_only_fields = ('id', 'email', 'is_premium')


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'color')


class SprintSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sprint
        fields = ('id', 'name', 'goal', 'status', 'start_date', 'end_date')


class ProjectSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    role = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = (
            'id', 'name', 'key', 'description', 'status', 'priority',
            'start_date', 'due_date', 'owner', 'role', 'created_at',
        )
        read_only_fields = ('id', 'key', 'owner', 'created_at')

    def get_role(self, obj):
        request = self.context.get('request')
        if not request:
            return None
        member = obj.members.filter(user=request.user).first()
        return member.role if member else None


class TaskSerializer(serializers.ModelSerializer):
    assignee = UserSerializer(read_only=True)
    assignee_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False
    )
    sprint_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Task
        fields = (
            'id', 'project', 'sprint_id', 'assignee', 'assignee_id',
            'parent_task', 'project_sequence', 'type', 'title', 'description',
            'status', 'priority', 'estimated_min', 'due_date', 'created_at',
            'updated_at', 'tags', 'tag_ids', 'is_overdue',
        )
        read_only_fields = ('id', 'project', 'project_sequence', 'created_at', 'updated_at')

    def create(self, validated_data):
        tag_ids = validated_data.pop('tag_ids', [])
        task = super().create(validated_data)
        if tag_ids:
            task.tags.set(Tag.objects.filter(id__in=tag_ids, project=task.project))
        return task

    def update(self, instance, validated_data):
        tag_ids = validated_data.pop('tag_ids', None)
        task = super().update(instance, validated_data)
        if tag_ids is not None:
            task.tags.set(Tag.objects.filter(id__in=tag_ids, project=task.project))
        return task


class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ('id', 'task', 'user', 'content', 'created_at', 'updated_at', 'deleted_at')
        read_only_fields = ('id', 'task', 'user', 'created_at', 'updated_at', 'deleted_at')
