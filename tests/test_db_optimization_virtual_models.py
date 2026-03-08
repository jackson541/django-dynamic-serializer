"""
Database optimization tests with django-virtual-models.

Verifies that combining DynamicSerializerFieldsMixin + VirtualModelSerializer
with DynamicSerializerView + VirtualModelListAPIView/VirtualModelRetrieveAPIView
produces the correct query counts and response structures.

The integration relies on:
1. DynamicSerializerView._get_empty_serializer() — creates a field-filtered
   serializer on GET requests.
2. GenericVirtualModelViewMixin.get_queryset() — calls _get_empty_serializer()
   then VirtualModelSerializer.get_optimized_queryset() which uses LookupFinder
   to inspect the filtered fields and generate only the needed prefetches.

Skipped when django-virtual-models is not installed.
"""
import unittest

from django.test import TestCase
from rest_framework.test import APIRequestFactory

from .models import Author, Book, Library, Review
from .virtual_models import HAS_VIRTUAL_MODELS


@unittest.skipUnless(HAS_VIRTUAL_MODELS, "django-virtual-models is not installed")
class VirtualModelSerializerDirectTest(TestCase):
    """Serializer-level tests for BookVirtualSerializer with VirtualModelSerializer."""

    @classmethod
    def setUpTestData(cls):
        cls.library = Library.objects.create(name="Virtual Lib", city="Gotham")
        cls.author1 = Author.objects.create(name="VM Author A", birth_year=1965)
        cls.author2 = Author.objects.create(name="VM Author B", birth_year=1990)

        cls.book1 = Book.objects.create(
            title="VM Book One", isbn="3333333333333",
            author=cls.author1, library=cls.library,
        )
        cls.book2 = Book.objects.create(
            title="VM Book Two", isbn="4444444444444",
            author=cls.author2, library=cls.library,
        )

        for book in (cls.book1, cls.book2):
            Review.objects.create(rating=5, comment="Amazing", book=book)
            Review.objects.create(rating=2, comment="Meh", book=book)

    def test_virtual_serializer_has_virtual_model(self):
        """BookVirtualSerializer.Meta.virtual_model is VirtualBook."""
        from .serializers import BookVirtualSerializer
        from .virtual_models import VirtualBook

        self.assertIs(BookVirtualSerializer.Meta.virtual_model, VirtualBook)

    def test_virtual_serializer_field_selection(self):
        """Field selection strips unwanted fields from VirtualModelSerializer."""
        from .serializers import BookVirtualSerializer

        fields = ["id", "title"]
        serializer = BookVirtualSerializer(
            instance=None, fields=fields,
            context={"request": None, "view": None},
        )
        self.assertEqual(set(serializer.fields.keys()), {"id", "title"})

    def test_virtual_serializer_nested_field_selection(self):
        """Nested field selection works through VirtualModelSerializer."""
        from .serializers import BookVirtualSerializer

        fields = [
            "id",
            "title",
            {"object_name": "author", "fields": ["id", "name"]},
        ]
        serializer = BookVirtualSerializer(
            instance=None, fields=fields,
            context={"request": None, "view": None},
        )
        self.assertEqual(set(serializer.fields.keys()), {"id", "title", "author"})
        self.assertEqual(
            set(serializer.fields["author"].fields.keys()), {"id", "name"},
        )


@unittest.skipUnless(HAS_VIRTUAL_MODELS, "django-virtual-models is not installed")
class VirtualModelViewEmptySerializerTest(TestCase):
    """
    Tests that _get_empty_serializer on virtual model views produces a
    field-filtered VirtualModelSerializer, which drives the LookupFinder
    to generate only the needed prefetches.
    """

    @classmethod
    def setUpTestData(cls):
        cls.library = Library.objects.create(name="Lib", city="City")
        cls.author = Author.objects.create(name="Author", birth_year=1970)
        Book.objects.create(
            title="Book", isbn="0000000000000",
            author=cls.author, library=cls.library,
        )

    def _build_view(self, view_cls, method="GET"):
        """Instantiate a view with a fake request for introspection."""
        factory = APIRequestFactory()
        if method == "GET":
            request = factory.get("/")
        else:
            request = factory.post("/")
        view = view_cls()
        view.request = request
        view.format_kwarg = None
        view.kwargs = {}
        return view

    def test_list_view_empty_serializer_has_all_declared_fields(self):
        """BookVirtualModelListView._get_empty_serializer includes author and reviews."""
        from .views import BookVirtualModelListView

        view = self._build_view(BookVirtualModelListView)
        serializer = view._get_empty_serializer()
        self.assertEqual(
            set(serializer.fields.keys()), {"id", "title", "author", "reviews"},
        )

    def test_flat_view_empty_serializer_strips_nested(self):
        """BookVirtualModelFlatListView._get_empty_serializer keeps only flat fields."""
        from .views import BookVirtualModelFlatListView

        view = self._build_view(BookVirtualModelFlatListView)
        serializer = view._get_empty_serializer()
        self.assertEqual(set(serializer.fields.keys()), {"id", "title"})

    def test_author_only_view_empty_serializer_strips_reviews(self):
        """BookVirtualModelAuthorOnlyListView._get_empty_serializer includes author but not reviews."""
        from .views import BookVirtualModelAuthorOnlyListView

        view = self._build_view(BookVirtualModelAuthorOnlyListView)
        serializer = view._get_empty_serializer()
        self.assertEqual(
            set(serializer.fields.keys()), {"id", "title", "author"},
        )
        self.assertNotIn("reviews", serializer.fields)

    def test_detail_view_empty_serializer_has_all_fields(self):
        """BookVirtualModelDetailView._get_empty_serializer includes all nested fields."""
        from .views import BookVirtualModelDetailView

        view = self._build_view(BookVirtualModelDetailView)
        serializer = view._get_empty_serializer()
        self.assertEqual(
            set(serializer.fields.keys()),
            {"id", "title", "isbn", "author", "reviews"},
        )


@unittest.skipUnless(HAS_VIRTUAL_MODELS, "django-virtual-models is not installed")
class VirtualModelQueryCountTest(TestCase):
    """
    End-to-end query count tests through views using VirtualModelListAPIView
    and VirtualModelRetrieveAPIView. Demonstrates that dynamic field selection
    drives the LookupFinder to skip unnecessary prefetches.
    """

    @classmethod
    def setUpTestData(cls):
        cls.library = Library.objects.create(name="VM Lib", city="VM City")
        cls.author1 = Author.objects.create(name="VM Author A", birth_year=1965)
        cls.author2 = Author.objects.create(name="VM Author B", birth_year=1990)

        cls.book1 = Book.objects.create(
            title="VM Book One", isbn="3333333333333",
            author=cls.author1, library=cls.library,
        )
        cls.book2 = Book.objects.create(
            title="VM Book Two", isbn="4444444444444",
            author=cls.author2, library=cls.library,
        )

        for book in (cls.book1, cls.book2):
            Review.objects.create(rating=5, comment="Amazing", book=book)
            Review.objects.create(rating=2, comment="Meh", book=book)

    def test_full_nested_3_queries(self):
        """
        With author and reviews: 3 queries.
          1) SELECT books
          2) SELECT authors WHERE id IN (…)  (prefetch via VirtualAuthor)
          3) SELECT reviews WHERE book_id IN (…) (prefetch via VirtualReview)
        """
        from rest_framework.test import APIClient

        client = APIClient()
        with self.assertNumQueries(3):
            response = client.get("/integration/books/virtual/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)

    def test_author_only_2_queries(self):
        """
        With author but no reviews: 2 queries.
          1) SELECT books
          2) SELECT authors WHERE id IN (…) (prefetch via VirtualAuthor)
        Reviews prefetch is skipped because the field was stripped.
        """
        from rest_framework.test import APIClient

        client = APIClient()
        with self.assertNumQueries(2):
            response = client.get("/integration/books/virtual-author/")
        self.assertEqual(response.status_code, 200)

    def test_flat_1_query(self):
        """
        With flat fields only: 1 query.
          1) SELECT books
        No prefetches because all nested serializers are stripped.
        """
        from rest_framework.test import APIClient

        client = APIClient()
        with self.assertNumQueries(1):
            response = client.get("/integration/books/virtual-flat/")
        self.assertEqual(response.status_code, 200)

    def test_detail_view_3_queries(self):
        """
        RetrieveAPIView with full nested fields: 3 queries.
          1) SELECT book WHERE id = X
          2) SELECT authors WHERE id IN (…) (prefetch via VirtualAuthor)
          3) SELECT reviews WHERE book_id IN (…) (prefetch via VirtualReview)
        """
        from rest_framework.test import APIClient

        client = APIClient()
        with self.assertNumQueries(3):
            response = client.get(f"/integration/books/virtual/{self.book1.pk}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], self.book1.pk)

    def test_query_count_scales_constantly(self):
        """
        Adding a third book does NOT increase query count; prefetch_related
        batches all related objects in a single query per relation.
        """
        from rest_framework.test import APIClient

        author3 = Author.objects.create(name="VM Author C", birth_year=2000)
        Book.objects.create(
            title="VM Book Three", isbn="5555555555555",
            author=author3, library=self.library,
        )
        client = APIClient()
        with self.assertNumQueries(3):
            response = client.get("/integration/books/virtual/")
        self.assertEqual(len(response.json()), 3)
