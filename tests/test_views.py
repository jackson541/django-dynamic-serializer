"""
View response tests for DynamicSerializerView.

Asserts that list/detail endpoints return only the fields declared by
get_serializer_fields(), that nested structures match the spec, and that
POST requests ignore field selection. Also verifies NotImplementedError
when get_serializer_fields() is not implemented.
"""
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Author, Book, Library, Review


class ViewResponseTest(TestCase):
    """Tests that API responses contain only the declared serializer fields."""

    @classmethod
    def setUpTestData(cls):
        cls.library = Library.objects.create(name="Central Library", city="Springfield")
        cls.author = Author.objects.create(name="Jane Doe", birth_year=1980)
        cls.book = Book.objects.create(
            title="Test Book",
            isbn="9781234567890",
            author=cls.author,
            library=cls.library,
        )
        Review.objects.create(rating=5, comment="Great!", book=cls.book)
        Review.objects.create(rating=3, comment="Okay", book=cls.book)

    def setUp(self):
        self.client = APIClient()

    def test_list_returns_only_declared_fields(self):
        """GET list response JSON keys match the view's get_serializer_fields()."""
        response = self.client.get("/books/")
        self.assertEqual(response.status_code, 200)
        item = response.json()[0]
        self.assertEqual(set(item.keys()), {"id", "title", "author"})

    def test_detail_returns_only_declared_fields(self):
        """GET detail response includes only the declared top-level fields."""
        response = self.client.get(f"/books/{self.book.pk}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(set(data.keys()), {"id", "title", "isbn", "author", "reviews"})

    def test_nested_fields_in_response(self):
        """Nested author object contains only the declared sub-fields (id, name)."""
        response = self.client.get("/books/")
        self.assertEqual(response.status_code, 200)
        author_data = response.json()[0]["author"]
        self.assertEqual(set(author_data.keys()), {"id", "name"})

    def test_detail_nested_reviews(self):
        """Detail view returns reviews with only id, rating, comment as declared."""
        response = self.client.get(f"/books/{self.book.pk}/")
        data = response.json()
        self.assertEqual(len(data["reviews"]), 2)
        self.assertEqual(
            set(data["reviews"][0].keys()), {"id", "rating", "comment"}
        )

    def test_post_ignores_field_selection(self):
        """POST to create uses full serializer; field selection applies only to GET."""
        payload = {
            "title": "New Book",
            "isbn": "9789876543210",
            "author": self.author.pk,
            "library": self.library.pk,
        }
        response = self.client.post("/books/create/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertIn("id", response.json())
        self.assertIn("title", response.json())

    def test_flat_list_returns_only_flat_fields(self):
        """Flat-only endpoint returns only id and title (no nested relations)."""
        response = self.client.get("/books/flat/")
        self.assertEqual(response.status_code, 200)
        item = response.json()[0]
        self.assertEqual(set(item.keys()), {"id", "title"})

    def test_get_serializer_fields_not_implemented(self):
        """A view that does not implement get_serializer_fields() raises NotImplementedError."""
        with self.assertRaises(NotImplementedError):
            self.client.get("/books/missing/")
