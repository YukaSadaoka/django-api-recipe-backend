from rest_framework import serializers

from core.models import Article


class ArticleSerializer(serializers.ModelSerializer):
    """Serializers for Article object"""

    class Meta:
        model = Article
        fields = ('id', 'title', 'author', 'body', 'date')
        read_only_fields = ('id',)


class ArticleImageSerializer(serializers.ModelSerializer):
    """Serializer for uploading images"""

    class Meta:
        model = Article
        fields = ('id', 'image')
        read_only_fields = ('id', )