from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from accounts.models import User
from vendors.models import Vendor


class VendorAPITests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="vendor_test_user",
            password="TestPassword!739",
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.vendor_data = {
            "vendor_code": "VEN-001",
            "legal_name": "Example Technologies Private Limited",
            "display_name": "Example Technologies",
            "gstin": "29ABCDE1234F1Z5",
            "pan": "ABCDE1234F",
            "contact_person": "Test Contact",
            "email": "vendor@example.com",
            "phone": "9876543210",
            "address_line1": "100 Example Road",
            "address_line2": "",
            "city": "Bengaluru",
            "state": "Karnataka",
            "postal_code": "560001",
            "payment_terms_days": 30,
            "status": "PENDING",
        }

    def test_create_vendor(self):
        response = self.client.post(
            "/api/vendors/",
            self.vendor_data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Vendor.objects.count(), 1)

        vendor = Vendor.objects.get(vendor_code="VEN-001")
        self.assertEqual(vendor.created_by, self.user)

    def test_list_vendors(self):
        Vendor.objects.create(
            **{
                key: value
                for key, value in self.vendor_data.items()
                if key not in {"created_by"}
            },
            created_by=self.user,
        )

        response = self.client.get("/api/vendors/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_gstin_is_rejected(self):
        data = self.vendor_data.copy()
        data["gstin"] = "INVALID-GSTIN"

        response = self.client.post(
            "/api/vendors/",
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(Vendor.objects.count(), 0)

    def test_duplicate_gstin_is_rejected(self):
        first_response = self.client.post(
            "/api/vendors/",
            self.vendor_data,
            format="json",
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_201_CREATED,
        )

        duplicate_data = self.vendor_data.copy()
        duplicate_data["vendor_code"] = "VEN-002"

        response = self.client.post(
            "/api/vendors/",
            duplicate_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_unauthenticated_access_is_denied(self):
        self.client.force_authenticate(user=None)

        response = self.client.get("/api/vendors/")

        self.assertIn(
            response.status_code,
            [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ],
        )