from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

# Create your tests here.


class JWTTokenEndpointTests(APITestCase):
    def test_login_and_refresh_return_usable_tokens(self):
        user_model = get_user_model()
        user_model.objects.create_user(
            username="jwt_smoke_user",
            password="SafeTestPassword!123",
        )

        login = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "jwt_smoke_user", "password": "SafeTestPassword!123"},
            format="json",
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        self.assertIn("access", login.data)
        self.assertIn("refresh", login.data)

        refresh = self.client.post(
            reverse("token_refresh"),
            {"refresh": login.data["refresh"]},
            format="json",
        )
        self.assertEqual(refresh.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh.data)
