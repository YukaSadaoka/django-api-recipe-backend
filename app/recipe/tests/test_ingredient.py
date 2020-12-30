from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Ingredient, Recipe

from recipe.serializers import IngredientSerializer


INGREDIENT_URL = reverse('recipe:ingredient-list')


def detail_url(ingredient_url):
    """Create detail url for PUT and PATCH"""
    return reverse('recipe:ingredient-detail', args=[ingredient_url])


class PublicIngredientApiTests(TestCase):
    """Test the publicly available ingredient API"""

    def setUp(self):
        self.client = APIClient()

    # From here INGREDIENT_URL testing
    def test_login_not_required_to_retrieve(self):
        """Test that login not required to retrieve ingredients"""
        res = self.client.get(INGREDIENT_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_login_required_to_create(self):
        """Test login required to create ingredients"""
        payload = {'name': 'Peach'}
        res = self.client.post(INGREDIENT_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientApiTests(TestCase):
    """Test the privatly available ingredient API"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email='myemail@look.com',
            password='Password123'
        )
        self.client.force_authenticate(self.user)

    def test_retrieving_ingredient_list(self):
        """Test retrieving ingredients"""
        Ingredient.objects.create(user=self.user, name='Potato')
        Ingredient.objects.create(user=self.user, name='Soy Sauce')

        res = self.client.get(INGREDIENT_URL)

        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_any_user_can_retrieve_ingredients(self):
        """Test that return ingredients to other authenticated user"""
        otherUser = get_user_model().objects.create_user(
            email='django@look.com',
            password='Test123'
        )
        otherClient = APIClient()
        otherClient.force_authenticate(otherUser)

        ingOther = Ingredient.objects.create(user=otherUser, name='Pepper')
        ingUser = Ingredient.objects.create(user=self.user, name='butter')
        resultUser = self.client.get(INGREDIENT_URL)
        resultOther = otherClient.get(INGREDIENT_URL)

        serializerOther = IngredientSerializer(ingOther)
        serializerUser = IngredientSerializer(ingUser)

        self.assertEqual(resultUser.status_code, status.HTTP_200_OK)
        self.assertEqual(resultOther.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resultUser.data), len(resultOther.data))
        self.assertEqual(resultUser.data[0]['name'], resultOther.data[0]['name'])
        self.assertEqual(resultUser.data[1]['name'], resultOther.data[1]['name'])
        self.assertIn(serializerUser.data, resultOther.data)
        self.assertIn(serializerUser.data, resultUser.data)
        self.assertIn(serializerOther.data, resultOther.data)
        self.assertIn(serializerOther.data, resultUser.data)

    def test_create_ingredient_successful(self):
        """Test create a new ingredient"""
        payload = {'name': 'Cabbage'}
        self.client.post(INGREDIENT_URL, payload)

        exist = Ingredient.objects.filter(
            user=self.user,
            name=payload['name']
        ).exists()

        self.assertTrue(exist)

    def test_create_invalid_ingredient(self):
        """Test providing invalid ingredient"""
        payload = {'name': ''}
        res = self.client.post(INGREDIENT_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_full_update_with_authorized_user(self):
        """Test authorized user can PUT ingredient"""
        ingredient = Ingredient.objects.create(user=self.user, name='Margarine')
        payload = {'name': 'Butter'}

        url = detail_url(ingredient.id)
        res = self.client.put(url, payload)

        ingredient.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(ingredient.name, payload['name'])

    def test_partially_update_with_authorized_user(self):
        """Test authorized user can PATCH ingredient"""
        ingredient = Ingredient.objects.create(user=self.user, name='Tomato')
        payload = {'name': 'Cherry Tomato'}

        url = detail_url(ingredient.id)
        res = self.client.patch(url, payload)

        ingredient.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(ingredient.name, payload['name'])

    def test_full_update_required_to_login(self):
        """Test update ingredient required to login"""
        ingredient = Ingredient.objects.create(user=self.user, name='Kale')
        payload = {'name': 'Cabbage'}
        url = detail_url(ingredient.id)

        other = APIClient()
        res = other.put(url, payload)

        ingredient.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotEqual(ingredient.name, payload['name'])

    def test_partially_update_required_to_login(self):
        """Test partially update ingredient required to login"""
        ingredient = Ingredient.objects.create(user=self.user, name='Orange')
        url = detail_url(ingredient.id)
        payload = {'name': 'Clementine'}

        other = APIClient()
        res = other.patch(url, payload)

        ingredient.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotEqual(ingredient.name, payload['name'])

    # From here testing assigned_only functionality
    def test_retrieve_ingredients_assigned_to_recipes(self):
        """Test filtering ingredients by those assigned to recipes"""
        ingredient1 = Ingredient.objects.create(user=self.user, name='Apple')
        ingredient2 = Ingredient.objects.create(user=self.user, name='Turkey')
        recipe = Recipe.objects.create(
            title='Apple crumble',
            time_minutes=5,
            price=10,
            user=self.user
        )
        recipe.ingredients.add(ingredient1)

        res = self.client.get(INGREDIENT_URL, {'assigned_only': 1})

        serializer1 = IngredientSerializer(ingredient1)
        serializer2 = IngredientSerializer(ingredient2)
        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_retrieve_ingredient_assigned_unique(self):
        """Test filtering ingredients by assigned returns unique items"""
        ingredient = Ingredient.objects.create(user=self.user, name='Eggs')
        Ingredient.objects.create(user=self.user, name='Cheese')
        recipe1 = Recipe.objects.create(
            title='Eggs Benedict',
            time_minutes=10,
            price=8.50,
            user=self.user
        )
        recipe1.ingredients.add(ingredient)
        recipe2 = Recipe.objects.create(
            title='Sunnyside eggs toast',
            time_minutes=5,
            price=5.00,
            user=self.user
        )
        recipe2.ingredients.add(ingredient)

        res = self.client.get(INGREDIENT_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)
