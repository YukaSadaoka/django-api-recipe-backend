from unittest.mock import patch
from datetime import datetime
from django.test import TestCase
from django.contrib.auth import get_user_model

from core import models


def sample_user(email='myemail@look.com', password='Password123'):
    """Create a sample user"""
    return get_user_model().objects.create_superuser(email, password)


class ModelTests(TestCase):

    # From here User model testing
    def test_create_user(self):
        """Test creating a new user with an email is successful"""
        email = 'myemail@look.com'
        password = 'Password123'
        user = get_user_model().objects.create_user(
            email=email,
            password=password
        )

        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))

    def test_new_user_email(self):
        """Test the email for a new user is normalized"""
        email = 'myemail@LOOK.COM'
        user = get_user_model().objects.create_user(email, 'test123')

        self.assertEqual(user.email, email.lower())

    def test_new_user_invalid_email(self):
        """Test creating user who doesn't have email raises error"""
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user(None, 'Pass123')

    def test_create_new_superuser(self):
        """Test creating a new superuser"""
        email = 'myemail@LOOK.COM'
        user = get_user_model().objects.create_superuser(email, 'test123')

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_active)

    # From here Tag model testing
    def test_tag_str(self):
        """Test the tag string representation"""
        tag = models.Tag.objects.create(
            user=sample_user(),
            name='Vegan'
        )

        self.assertEqual(str(tag), tag.name)

    # From here Ingredient model testing
    def test_ingredient_str(self):
        """Test the ingredient string representation"""
        ing = models.Ingredient.objects.create(
            user=sample_user(),
            name='Tomato'
        )

        self.assertEqual(str(ing), ing.name)

    # From here Recipe object model testing
    def test_recipe_str(self):
        """Test the recipe string representation"""
        recipe = models.Recipe.objects.create(
            user=sample_user(),
            title='Tomato soup with garlic breads',
            time_minutes=15,
            price=3.50,
            description="This easy vegan recipe which is perfect for winter can be done within 15 minutes!",
            instruction="1. crush Tomatoes in a pot with a wooden spatula. Season it with pepper and salt.\n" +
                        "2. Cat garlic clove into halve and rub it on sliced bread. Brush the surface with olive oil"
        )

        self.assertEqual(str(recipe), recipe.title)

    # From here image field testing
    @patch('uuid.uuid4')
    def test_recipe_file_name_uuid(self, mock_uuid):
        """Test that image is saved in the correct location"""
        uuid = 'test-uuid'
        mock_uuid.return_value = uuid
        file_path = models.recipe_image_file_path(None, 'myimage.jpg')
        print(file_path)
        expected_path = f'uploads/recipe/{uuid}.jpg'

        print(expected_path)
        self.assertEqual(expected_path, file_path)

    # def test_image_str(self):
    #     """Test a string representation for Image model"""
    #     image = models.Image.objects.create(
    #         title='Garlic bread image'
    #     )

    def test_article_str(self):
        """Test the article string representation"""
        article = models.Article.objects.create(
            user=sample_user(),
            title='Christmas dinner leftover ideas',
            author='Yuka Sadaoka',
            body='Christmas dinner leftover ideas',
            date=datetime.now(),
        )

        self.assertEqual(str(article), article.title)

    @patch('uuid.uuid4')
    def test_image_upload(self, mock_uuid):
        """Test uploading image to article"""
        """@patch invokes uuid4()"""
        uuid = 'test-uuid'
        mock_uuid.return_value = uuid
        filepath = models.article_image_file_path(None, 'sample.jpg')

        expected_path = f'uploads/article/{uuid}.jpg'
        self.assertEqual(expected_path, filepath)
