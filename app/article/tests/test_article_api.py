import tempfile
import os
from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils.timezone import now

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Article

from article.serializers import ArticleSerializer

ARTICLE_URL = reverse('article:article-list')


def image_upload_url(article_id):
    """Return URL for uploading image"""
    return reverse('article:article-upload-image', args=[article_id])


def detail_url(article_id):
    """Return article detail URL"""
    return reverse('article:article-detail', args=[article_id])


def sample_article(user, **params):
    """Create and return a sample article"""
    defaults = {
        'title': 'Sample title',
        'author': 'Sample Author',
        'body': 'This is a sample article',
        'date': now()
    }

    defaults.update(params)
    return Article.objects.create(user=user, **defaults)


class PublicArticleApiTests(TestCase):
    """Test unauthenticated API access"""

    def setUp(self):
        self.client = APIClient()

    # From here ARTICLE_URL test
    def test_article_view(self):
        """Test unauthenticated user can view articles"""
        res = self.client.get(ARTICLE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)


class PrivateArticleApiTests(TestCase):
    """Test authenticated article API access"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='email@email.com',
            password='Password123'
        )

        self.client = APIClient()
        self.client.force_authenticate(self.user)

    # From here ARTICLE_URL test
    def test_retrieve_article(self):
        """Test retrieving a list of articles"""
        sample_article(self.user)
        sample_article(self.user)

        res = self.client.get(ARTICLE_URL)

        articles = Article.objects.all().order_by('-id')
        serializer = ArticleSerializer(articles, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), len(serializer.data))
        self.assertEqual(res.data, serializer.data)

    def test_partial_update(self):
        """Test updating article with patch"""
        article = sample_article(self.user)
        url = detail_url(article.id)
        payload = {'title': 'Summar cocktail ideas', 'date': now()}
        res = self.client.patch(url, payload)

        article.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(article.title, payload['title'])

    def test_full_update_article(self):
        """Test authenticated user updates article"""
        article = sample_article(self.user)
        url = detail_url(article.id)

        payload = {
            'title': 'Bread baking tips for absolute beginners',
            'author': 'Baking Master',
            'body': 'If you are wondering how to make '
                    'a very first baking successful',
            'date': now()
        }
        res = self.client.put(url, payload)

        article.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(article.title, payload['title'])
        self.assertEqual(article.author, payload['author'])
        self.assertEqual(article.body, payload['body'])
        self.assertEqual(article.date, payload['date'])

    def test_partial_update_limited_to_user(self):
        """Test unauthorized user update partial article"""
        other = APIClient()
        article = sample_article(self.user)
        url = detail_url(article.id)

        payload = {'title': 'Christmas Decoration trend 2020'}
        res = other.put(url, payload)

        article.refresh_from_db()
        self.assertNotEqual(article.title, payload['title'])
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_full_update_limited_to_user(self):
        """Test unauthorized user update full article"""
        other = APIClient()
        article = sample_article(self.user)
        url = detail_url(article.id)

        payload = {
            'title': 'The best hit recipes in 2020',
            'author': 'Yuka Sadaoka',
            'body': 'This is the list of the most popular recipes 2020',
            'date': now()
        }
        res = other.put(url, payload)

        article.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotEqual(article.title, payload['title'])
        self.assertNotEqual(article.author, payload['author'])
        self.assertNotEqual(article.body, payload['body'])
        self.assertNotEqual(article.date, payload['date'])


# From here testing uploading image endpoint
class ArticleImageUploadTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email='email@email.com',
            password='Password123'
        )
        self.client.force_authenticate(self.user)
        self.article = sample_article(self.user)

    def tearDown(self):
        """Clean up image after testing in case"""
        self.article.image.delete()

    def test_upload_iamge_to_article(self):
        """Test uploading image to article"""
        url = image_upload_url(self.article.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as nt:
            img = Image.new('RGB', (10, 10))
            img.save(nt, format='JPEG')
            nt.seek(0)
            res = self.client.post(url, {'image': nt}, format='multipart')

        self.article.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.article.image.path))

    def test_upload_bad_image(self):
        """Test uploading bad image"""
        url = image_upload_url(self.article.id)
        res = self.client.post(url, {'image': 'none'}, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
