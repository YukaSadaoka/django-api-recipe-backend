from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from core.models import Tag, Recipe

from recipe.serializers import TagSerializer


TAGS_URL = reverse('recipe:tag-list')


def detail_url(tag_id):
    """Create tag detail URL"""
    return reverse('recipe:tag-detail', args=[tag_id])


class publicTagsApiTests(TestCase):
    """Test the public available tags API"""

    def setUp(self):
        self.client = APIClient()

    # From here TAGS_URL testing
    def test_login_not_required_to_retrieve(self):
        """Test that login not required for retrieving tags"""
        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_login_required_to_create(self):
        """Test that login required for creating tags"""
        payload = {'name': 'Breakfast'}
        res = self.client.post(TAGS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsApiTest(TestCase):
    """Test the authorized user tags API"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='email@look.com',
            password='Password123',
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    # From here TAGS_URL testing
    def test_retrieve_tags(self):
        """Test that retrieving tags with authenticated user"""
        Tag.objects.create(user=self.user, name='Vegan')
        Tag.objects.create(user=self.user, name='Meat')

        res = self.client.get(TAGS_URL)

        tag = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tag, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_unauthorized_user_can_retrieve_tags(self):
        """Test that retrieving tags made by authenticated user"""
        tag = Tag.objects.create(user=self.user, name='Breakfast')
        serializer = TagSerializer(tag)

        otherClient = APIClient()
        res = otherClient.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer.data, res.data)

    def test_full_update_tag_with_authorized_user(self):
        """Test authorized user can PUT tags"""
        tag = Tag.objects.create(user=self.user, name='Dinner')
        payload = {'name': 'Lunch'}

        url = detail_url(tag.id)
        res = self.client.put(url, payload)

        tag.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(tag.name, payload['name'])

    def test_partial_update_tag_with_authorized_user(self):
        """Test authorized user can PATCH tags"""
        tag = Tag.objects.create(user=self.user, name='Dinner')
        payload = {'name': 'Lunch'}

        url = detail_url(tag.id)
        res = self.client.patch(url, payload)

        tag.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(tag.name, payload['name'])

    def test_full_update_limited_to_user(self):
        """Test that unauthorized users can't PUT tags"""
        tag = Tag.objects.create(user=self.user, name='Dinner')

        url = detail_url(tag.id)
        payload = {'name': 'Lunch'}
        other = APIClient()
        res = other.put(url, payload)

        tag.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotEqual(tag.name, payload['name'])

    def test_partial_update_limited_to_user(self):
        """Test that unauthorized users can't PATCH tags"""
        tag = Tag.objects.create(user=self.user, name='Soup')

        url = detail_url(tag.id)
        other = APIClient()
        payload = {'name': 'Noodle'}
        res = other.patch(url, payload)

        tag.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotEqual(tag.name, payload['name'])

    def test_tags_limited_to_user(self):
        """Test that tags returned are for authenticated users"""
        otherUser = get_user_model().objects.create_user(
            email='django@look.com',
            password='Test123'
        )
        otherClient = APIClient()
        otherClient.force_authenticate(otherUser)

        tagOther = Tag.objects.create(user=otherUser, name='Dessert')
        tagUser = Tag.objects.create(user=self.user, name='Chinese foods')

        resultOther = otherClient.get(TAGS_URL)
        resultUser = self.client.get(TAGS_URL)

        serializerOther = TagSerializer(tagOther)
        serializerUser = TagSerializer(tagUser)

        self.assertEqual(resultUser.status_code, status.HTTP_200_OK)
        self.assertEqual(resultOther.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resultUser.data), len(resultOther.data))
        self.assertEqual(resultUser.data[0]['name'], resultOther.data[0]['name'])
        self.assertEqual(resultUser.data[1]['name'], resultOther.data[1]['name'])
        self.assertIn(serializerOther.data, resultOther.data)
        self.assertIn(serializerOther.data, resultUser.data)
        self.assertIn(serializerUser.data, resultOther.data)
        self.assertIn(serializerUser.data, resultUser.data)

    def test_create_tag_successful(self):
        """Test creating a new tag"""
        payload = {'name': 'Test tag'}
        self.client.post(TAGS_URL, payload)

        exists = Tag.objects.filter(
            user=self.user,
            name=payload['name']
        ).exists()

        self.assertTrue(exists)

    def test_create_tag_invalid(self):
        """Test creating a new tag invalid payload"""
        payload = {'name': ''}
        res = self.client.post(TAGS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # From here testing a assigned_only functionality
    def test_retrieve_tags_assigned_to_recipes(self):
        """Test filtering tags by those assigned to recipes"""
        tagOne = Tag.objects.create(user=self.user, name='Breakfast')
        tagTwo = Tag.objects.create(user=self.user, name='Lunch')
        recipe = Recipe.objects.create(
            title='Savory French Toast',
            time_minutes=20,
            price=10.00,
            user=self.user
        )
        recipe.tags.add(tagOne)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})

        serializerOne = TagSerializer(tagOne)
        serializerTwo = TagSerializer(tagTwo)
        self.assertIn(serializerOne.data, res.data)
        self.assertNotIn(serializerTwo.data, res.data)

    def test_retrieve_tags_assigned_unique(self):
        """Test filtering tags by assigned returns unique items"""
        tag = Tag.objects.create(user=self.user, name='Breakfast')
        Tag.objects.create(user=self.user, name='Lunch')
        recipeOne = Recipe.objects.create(
            title='Pancakes',
            time_minutes=12,
            price=12.00,
            user=self.user
        )
        recipeOne.tags.add(tag)

        recipeTwo = Recipe.objects.create(
            title='Porridge',
            time_minutes=5,
            price=2.80,
            user=self.user
        )
        recipeTwo.tags.add(tag)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)
