from django.urls import path, include
from rest_framework.routers import DefaultRouter

from article import views

router = DefaultRouter()
router.register('articles', views.ArticleViewSet)

app_name = 'article'

urlpatterns = [
    path('', include(router.urls))
]
