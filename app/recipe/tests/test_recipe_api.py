import tempfile
import os

from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag, Ingredient

from recipe.serializers import RecipeSerializer, RecipeDetailSerializer

RECIPE_URL = reverse('recipe:recipe-list')


def image_upload_url(recipe_id):
    """Return URL for recipe image upload"""
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


# Create helper functions
def detail_url(recipe_id):
    """Return recipe detail URL"""
    return reverse('recipe:recipe-detail', args=[recipe_id])


def sample_tag(user, name='Main course'):
    """Create and return a sample tag"""
    return Tag.objects.create(user=user, name=name)


def sample_ingredient(user, name='Salt'):
    """Create and return a sample ingredient"""
    return Ingredient.objects.create(user=user, name=name)


def sample_recipe(user, **params):
    """Create and return a sample recipe"""
    defaults = {
        'title': 'Sample recipe',
        'time_minutes': 10,
        'price': 5.00,
        'description': 'Sample description',
        'instruction': 'Sample instruction'
    }
    defaults.update(params)

    return Recipe.objects.create(user=user, **defaults)


class PublicRecipeApiTests(TestCase):
    """Test unauthenticated recipt API access"""

    def setUp(self):
        self.client = APIClient()

    # From here RECIPE_URL testing
    def test_recipe_retriving(self):
        """Test unauthenticated user"""
        res = self.client.get(RECIPE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_recipe_login_required_to_login(self):
        """Test login required to create a recipe"""
        payload = {
            'title': 'Cheesecake',
            'time_minutes': 45,
            'price': 5.00,
            'description': 'Basic gluten free cheesecake',
            'instruction': ('1. Mix room temperature cream cheese '
                            'and butter with sugar'
                            '2. Crush your favorite gluten free crackers '
                            'and put it on the bottom '
                            'of backing pan. Press them to make it flat.')
        }

        res = self.client.post(RECIPE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTests(TestCase):
    """Test authenticated recipe API access"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='myemail@look.com',
            password='Password123'
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    # From here RECIPE_URL testing
    def test_retrieve_recipes(self):
        """Test retrieving a list of recipes"""
        sample_recipe(user=self.user)
        sample_recipe(user=self.user)

        res = self.client.get(RECIPE_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_user_can_retrieve_all_recipes(self):
        """Test retrieving recipes for user"""
        otherUser = get_user_model().objects.create_user(
            email='other@look.com',
            password='Test123'
        )
        otherClient = APIClient()
        otherClient.force_authenticate(otherUser)

        recipe1 = sample_recipe(
                        user=otherUser,
                        title='Cheese Nachos',
                        time_minutes=20
                    )
        recipe2 = sample_recipe(
                        user=self.user,
                        title='Chow mei chicken noodle',
                        time_minutes=30
                    )

        resultUser = self.client.get(RECIPE_URL)
        resultOther = otherClient.get(RECIPE_URL)

        serializer1 = RecipeSerializer(recipe1)
        serializer2 = RecipeSerializer(recipe2)
        self.assertEqual(resultUser.status_code, status.HTTP_200_OK)
        self.assertEqual(resultOther.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resultUser.data), len(resultOther.data))
        self.assertEqual(resultOther.data, resultUser.data)
        self.assertIn(serializer1.data, resultUser.data)
        self.assertIn(serializer1.data, resultOther.data)
        self.assertIn(serializer2.data, resultUser.data)
        self.assertIn(serializer2.data, resultOther.data)

    # From here RECIPE_URL with detail testing
    def test_view_recipe_detail(self):
        """Test viewing a recipe detail"""
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        recipe.ingredients.add(sample_ingredient(user=self.user))

        url = detail_url(recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.data, serializer.data)

    # From here testing to create recipes in RECIPE_URL
    def test_create_recipe(self):
        """Test creating recipe"""
        payload = {
            'title': 'Cheesecake',
            'time_minutes': 45,
            'price': 5.00,
            'description': 'Basic gluten free cheesecake',
            'instruction': ('1. Mix room temperature cream cheese '
                            'and butter with sugar'
                            '2. Crush your favorite gluten free crackers '
                            'and put it on the bottom '
                            'of backing pan. Press them to make it flat.')
        }
        res = self.client.post(RECIPE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(recipe, key))

    def test_create_recipe_with_tags(self):
        """Test creating a recipe with tags"""
        tag1 = sample_tag(user=self.user, name='Noodle')
        tag2 = sample_tag(user=self.user, name='Vegan')
        payload = {
            'title': 'Asian veggie noodle',
            'tags': [tag1.id, tag2.id],
            'time_minutes': 60,
            'price': 10.00,
            'description': 'Healthy summer veggie noodle '
                           'with Peanut sauce',
            'instruction': """1. Cook your favorite asian noodle
                             according to the package\n
                            2. Cut summer vegetables into
                             half inch stripes\n"""
        }
        res = self.client.post(RECIPE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        tags = recipe.tags.all()
        self.assertEqual(tags.count(), 2)
        self.assertIn(tag1, tags)
        self.assertIn(tag2, tags)

    def test_create_recipe_with_ingredients(self):
        """Test creating a recipe with ingredients"""
        ingredient1 = sample_ingredient(user=self.user, name='Tofu')
        ingredient2 = sample_ingredient(user=self.user, name='Miso paste')
        payload = {
            'title': 'Japanese Miso soup with Tofu',
            'ingredients': [ingredient1.id, ingredient2.id],
            'time_minutes': 18,
            'price': 2.25,
            'description': 'Traditional Miso Soup Recipe',
            'instruction': """1. Boil water and take a 
                            broth from a sheet of Kelp\n
                            2. Cut all vegetables into a bite size\n"""
        }
        res = self.client.post(RECIPE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        ingredients = recipe.ingredients.all()
        self.assertEqual(ingredients.count(), 2)
        self.assertIn(ingredient1, ingredients)
        self.assertIn(ingredient2, ingredients)

    # From here test updating recipes
    def test_partial_update_recipe_authenticated_user(self):
        """Test updating a recipe with patch"""
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        new_tag = sample_tag(user=self.user, name='Curry')

        payload = {'title': 'Green Curry', 'tags': [new_tag.id]}
        url = detail_url(recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        tags = recipe.tags.all()
        self.assertEqual(len(tags), 1)
        self.assertIn(new_tag, tags)

    def test_full_update_recipe_with_authenticated_user(self):
        """Test updating a recipe with put"""
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        payload = {
            'title': 'Spaghetti carbonara',
            'time_minutes': 35,
            'price': 14.00,
            'description': 'Creamy Healthy Carbonara',
            'instruction': """1. Boil pasta and cut pancetta into cubes
                            and fry them in a pan\n
                            2. Prepare sauce. Mix eggs and
                             shredded parmesan cheese\n"""

        }
        url = detail_url(recipe.id)
        self.client.put(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.time_minutes, payload['time_minutes'])
        self.assertEqual(recipe.price, payload['price'])
        tags = recipe.tags.all()
        self.assertEqual(len(tags), 0)

    def test_full_update_recipe_with_unauthenticated_user(self):
        """Test that unauthenticated user PUT a recipe"""
        recipe = sample_recipe(user=self.user)
        payload = {
            'title': 'Spaghetti carbonara',
            'time_minutes': 35,
            'price': recipe.price,
            'description': 'Creamy Healthy Carbonara',
            'instruction': recipe.instruction
        }

        unauthedClient = APIClient()
        url = detail_url(recipe.id)
        res = unauthedClient.put(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotEqual(recipe.title, payload['title'])
        self.assertNotEqual(recipe.time_minutes, payload['time_minutes'])
        self.assertNotEqual(recipe.description, payload['description'])

    def test_partial_update_recipe_with_unauthenticated_user(self):
        """Test that unauthenticated user PATCH a recipe"""
        recipe = sample_recipe(user=self.user)
        payload = {'time_minutes': 20}

        unauthUser = APIClient()
        url = detail_url(recipe.id)
        res = unauthUser.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotEqual(recipe.time_minutes, payload['time_minutes'])


class RecipeImageUploadTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'myemail@look.com',
            'Test123'
        )

        self.client.force_authenticate(user=self.user)
        self.recipe = sample_recipe(user=self.user)

    def tearDown(self):
        """Delete images when test is done"""
        self.recipe.image.delete()

    # From here testing upload images
    def test_upload_image_to_recipe(self):
        """Test uploading an image to recipe"""
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as ntf:
            img = Image.new('RGB', (10, 10))
            img.save(ntf, format='JPEG')
            ntf.seek(0)
            res = self.client.post(url, {'image': ntf}, format='multipart')

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image"""
        url = image_upload_url(self.recipe.id)
        res = self.client.post(url, {'image': 'notimage'}, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # From here testing recipe filter
    def test_filter_recipes_by_tags(self):
        """Test returning recipes with specific tags"""
        recipeOne = sample_recipe(user=self.user, title='Vegan creamy pasta')
        recipeTwo = sample_recipe(user=self.user, title='Chickpeas salad')

        tagOne = sample_tag(user=self.user, name='Vegan')
        tagTwo = sample_tag(user=self.user, name='Salad')
        recipeOne.tags.add(tagOne)
        recipeTwo.tags.add(tagTwo)
        recipeThree = sample_recipe(user=self.user, title='Fish and Chips')

        res = self.client.get(
            RECIPE_URL,
            {'tags': f'{tagOne.id}, {tagTwo.id}'}
        )

        serializerOne = RecipeSerializer(recipeOne)
        serializerTwo = RecipeSerializer(recipeTwo)
        serializerThree = RecipeSerializer(recipeThree)
        self.assertIn(serializerOne.data, res.data)
        self.assertIn(serializerTwo.data, res.data)
        self.assertNotIn(serializerThree.data, res.data)

    def test_filter_recipes_by_ingredients(self):
        """Test returning recipes with specific ingredients"""
        recipeOne = sample_recipe(user=self.user, title='Korean Fried Rice')
        recipeTwo = sample_recipe(user=self.user, title='Garlic Hummus')

        ingOne = sample_ingredient(user=self.user, name='Rice')
        ingTwo = sample_ingredient(user=self.user, name='Chickpeas')

        recipeThree = sample_recipe(user=self.user, title='Quattro Formaggi')

        recipeOne.ingredients.add(ingOne)
        recipeTwo.ingredients.add(ingTwo)

        res = self.client.get(
            RECIPE_URL,
            {'ingredients': f'{ingOne.id}, {ingTwo.id}'}
        )

        serializerOne = RecipeSerializer(recipeOne)
        serializerTwo = RecipeSerializer(recipeTwo)
        serializerThree = RecipeSerializer(recipeThree)
        self.assertIn(serializerOne.data, res.data)
        self.assertIn(serializerTwo.data, res.data)
        self.assertNotIn(serializerThree.data, res.data)
