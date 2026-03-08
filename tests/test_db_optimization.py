"""
Database optimization tests without django-virtual-models.

Uses assertNumQueries to verify that dynamic field selection allows
fewer queries when only flat or selected nested fields are requested,
and that only()/select_related can be combined for lean queries.
"""
from django.test import TestCase

from .models import Author, Book, Library, Review
from .serializers import BookSerializer


class DatabaseOptimizationTest(TestCase):
    """Query count tests for dynamic serializers without virtual models."""

    @classmethod
    def setUpTestData(cls):
        cls.library = Library.objects.create(name="Main Library", city="Metropolis")
        cls.author1 = Author.objects.create(name="Author A", birth_year=1970)
        cls.author2 = Author.objects.create(name="Author B", birth_year=1985)

        cls.book1 = Book.objects.create(
            title="Book One", isbn="1111111111111",
            author=cls.author1, library=cls.library,
        )
        cls.book2 = Book.objects.create(
            title="Book Two", isbn="2222222222222",
            author=cls.author2, library=cls.library,
        )

        for book in (cls.book1, cls.book2):
            Review.objects.create(rating=5, comment="Excellent", book=book)
            Review.objects.create(rating=4, comment="Good", book=book)

    def test_full_fields_query_count(self):
        """Baseline: serializing all fields with select_related + prefetch_related uses 2 queries."""
        qs = Book.objects.select_related("author").prefetch_related("reviews")
        # 1 query for books+author (JOIN), 1 for prefetching reviews
        with self.assertNumQueries(2):
            serializer = BookSerializer(qs, many=True)
            serializer.data

    def test_reduced_fields_skip_prefetch(self):
        """Requesting only flat fields with only() yields a single query (no prefetch)."""
        qs = Book.objects.only("id", "title")
        with self.assertNumQueries(1):
            serializer = BookSerializer(qs, many=True, fields=["id", "title"])
            serializer.data

    def test_only_clause_with_dynamic_fields(self):
        """Combining only() with dynamic fields produces a single lean query."""
        qs = Book.objects.only("id", "title", "isbn")
        with self.assertNumQueries(1):
            serializer = BookSerializer(
                qs, many=True, fields=["id", "title", "isbn"]
            )
            serializer.data

    def test_nested_author_without_reviews(self):
        """Requesting nested author but not reviews uses select_related only (1 query)."""
        qs = Book.objects.select_related("author")
        fields = [
            "id",
            "title",
            {"object_name": "author", "fields": ["id", "name"]},
        ]
        # 1 query: books JOIN author (no reviews prefetch)
        with self.assertNumQueries(1):
            serializer = BookSerializer(qs, many=True, fields=fields)
            serializer.data
