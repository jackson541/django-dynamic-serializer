"""
End-to-end integration tests through the view layer.

Each test hits a real endpoint via APIClient and uses assertNumQueries to
count SQL statements. Four scenarios are covered:

1. Optimized queries (select_related + prefetch_related)
2. Unoptimized queries (N+1 demonstration)
3. Serializers using ``fields = '__all__'``
4. django-virtual-models optimization (skipped if not installed)
"""
import unittest

from django.test import TestCase
from rest_framework.test import APIClient

from .models import Author, Book, Library, Review
from .virtual_models import HAS_VIRTUAL_MODELS


class _IntegrationDataMixin:
    """Shared test data: 1 library, 2 authors, 2 books, 4 reviews."""

    @classmethod
    def setUpTestData(cls):
        cls.library = Library.objects.create(name="Central Library", city="Metropolis")
        cls.author1 = Author.objects.create(name="Author Alpha", birth_year=1970)
        cls.author2 = Author.objects.create(name="Author Beta", birth_year=1985)
        cls.book1 = Book.objects.create(
            title="Deep Dive", isbn="1111111111111",
            author=cls.author1, library=cls.library,
        )
        cls.book2 = Book.objects.create(
            title="Broad Overview", isbn="2222222222222",
            author=cls.author2, library=cls.library,
        )
        Review.objects.create(rating=5, comment="Excellent", book=cls.book1)
        Review.objects.create(rating=4, comment="Very good", book=cls.book1)
        Review.objects.create(rating=3, comment="Average", book=cls.book2)
        Review.objects.create(rating=2, comment="Below average", book=cls.book2)

    def setUp(self):
        self.client = APIClient()


# ---------------------------------------------------------------------------
# 1. Optimized queries (select_related + prefetch_related)
# ---------------------------------------------------------------------------

class IntegrationOptimizedQueriesTest(_IntegrationDataMixin, TestCase):
    """
    Queries when the view uses select_related('author') inside a
    Prefetch('books') and prefetch_related('reviews') on Book.
    """

    def test_full_nested_query_count(self):
        """
        3 queries:
        1) SELECT libraries
        2) SELECT books JOIN author WHERE library_id IN (…) (prefetch + select_related)
        3) SELECT reviews WHERE book_id IN (…) (prefetch)
        """
        with self.assertNumQueries(3):
            response = self.client.get("/integration/library/optimized/")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(len(data), 1)
        lib = data[0]
        self.assertEqual(set(lib.keys()), {"id", "name", "city", "books"})
        self.assertEqual(len(lib["books"]), 2)

        book = lib["books"][0]
        self.assertEqual(
            set(book.keys()), {"id", "title", "isbn", "author", "reviews"}
        )
        self.assertIn("name", book["author"])
        self.assertGreaterEqual(len(book["reviews"]), 1)

    def test_partial_fields_same_queryset(self):
        """
        3 queries (same optimized queryset is evaluated regardless of field
        selection):
        1) SELECT libraries
        2) SELECT books JOIN author WHERE library_id IN (…)
        3) SELECT reviews WHERE book_id IN (…)

        Dynamic fields reduce payload but the queryset still prefetches.
        """
        with self.assertNumQueries(3):
            response = self.client.get("/integration/library/optimized-partial/")
        self.assertEqual(response.status_code, 200)

    def test_partial_fields_response_structure(self):
        """Response contains only id/name on library and id/title on books."""
        response = self.client.get("/integration/library/optimized-partial/")
        lib = response.json()[0]
        self.assertEqual(set(lib.keys()), {"id", "name", "books"})

        book = lib["books"][0]
        self.assertEqual(set(book.keys()), {"id", "title"})


# ---------------------------------------------------------------------------
# 2. Unoptimized queries (N+1)
# ---------------------------------------------------------------------------

class IntegrationUnoptimizedQueriesTest(_IntegrationDataMixin, TestCase):
    """
    Queries when the view uses Library.objects.all() with no
    select_related / prefetch_related — shows the N+1 problem.
    """

    def test_full_nested_causes_n_plus_1(self):
        """
        6 queries (N+1 at author and reviews level):
        1) SELECT libraries
        2) SELECT books WHERE library_id = 1  (lazy books.all())
        3) SELECT author WHERE id = A1        (lazy FK, book 1)
        4) SELECT author WHERE id = A2        (lazy FK, book 2)
        5) SELECT reviews WHERE book_id = B1  (lazy reverse FK, book 1)
        6) SELECT reviews WHERE book_id = B2  (lazy reverse FK, book 2)
        """
        with self.assertNumQueries(6):
            response = self.client.get("/integration/library/unoptimized/")
        self.assertEqual(response.status_code, 200)

        lib = response.json()[0]
        self.assertEqual(len(lib["books"]), 2)
        self.assertIn("author", lib["books"][0])
        self.assertIn("reviews", lib["books"][0])

    def test_flat_fields_avoids_n_plus_1(self):
        """
        1 query only:
        1) SELECT libraries

        Dynamic fields strip nested books entirely, so books.all() is
        never accessed and no N+1 occurs.
        """
        with self.assertNumQueries(1):
            response = self.client.get("/integration/library/unoptimized-flat/")
        self.assertEqual(response.status_code, 200)

        lib = response.json()[0]
        self.assertEqual(set(lib.keys()), {"id", "name"})

    def test_n_plus_1_grows_with_data(self):
        """
        Adding a third book increases the query count by 2 (one for its
        author FK and one for its reviews), proving linear N+1 growth.

        Before: 6 queries (2 books)
        After:  8 queries (3 books)
        Pattern: 2 + 2*N where N = number of books.
        """
        author3 = Author.objects.create(name="Author Gamma", birth_year=1995)
        book3 = Book.objects.create(
            title="Third Book", isbn="3333333333333",
            author=author3, library=self.library,
        )
        Review.objects.create(rating=1, comment="Poor", book=book3)

        with self.assertNumQueries(8):
            response = self.client.get("/integration/library/unoptimized/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()[0]["books"]), 3)


# ---------------------------------------------------------------------------
# 3. __all__ serializers
# ---------------------------------------------------------------------------

class IntegrationAllFieldsSerializerTest(_IntegrationDataMixin, TestCase):
    """
    Queries when serializers use ``fields = '__all__'`` instead of
    explicit field lists. Verifies the mixin works identically.
    """

    def test_all_fields_serializer_with_nested_selection(self):
        """
        3 queries (same as explicit-field optimized):
        1) SELECT libraries
        2) SELECT books JOIN author WHERE library_id IN (…)
        3) SELECT reviews WHERE book_id IN (…)

        Response includes only the dynamically declared fields.
        """
        with self.assertNumQueries(3):
            response = self.client.get("/integration/library/all-fields/")
        self.assertEqual(response.status_code, 200)

        lib = response.json()[0]
        self.assertEqual(set(lib.keys()), {"id", "name", "books"})

        book = lib["books"][0]
        self.assertEqual(set(book.keys()), {"id", "title", "author"})
        self.assertEqual(set(book["author"].keys()), {"id", "name"})

    def test_all_fields_serializer_excludes_unrequested_fields(self):
        """
        '__all__' exposes extra model fields (like library PK on Book,
        or book PK on Review). Dynamic field selection strips them so
        they do not appear in the response.
        """
        response = self.client.get("/integration/library/all-fields/")
        book = response.json()[0]["books"][0]
        self.assertNotIn("isbn", book)
        self.assertNotIn("library", book)
        self.assertNotIn("reviews", book)

    def test_all_fields_flat_only(self):
        """
        Requesting flat fields on an __all__ serializer returns only
        those fields; all model-level extras are excluded.
        """
        response = self.client.get("/integration/library/all-fields/")
        lib = response.json()[0]
        self.assertNotIn("city", lib)
        self.assertEqual(set(lib.keys()), {"id", "name", "books"})


# ---------------------------------------------------------------------------
# 4. django-virtual-models (VirtualModelSerializer + VirtualModelListAPIView)
# ---------------------------------------------------------------------------

@unittest.skipUnless(HAS_VIRTUAL_MODELS, "django-virtual-models is not installed")
class IntegrationVirtualModelsTest(_IntegrationDataMixin, TestCase):
    """
    Queries when views use VirtualModelListAPIView / VirtualModelRetrieveAPIView
    with BookVirtualSerializer (VirtualModelSerializer).

    The query optimization is fully automatic: GenericVirtualModelViewMixin
    calls _get_empty_serializer() (field-filtered by DynamicSerializerView),
    then VirtualModelSerializer.get_optimized_queryset() uses LookupFinder
    to generate only the needed prefetches.
    """

    def test_virtual_model_full_nested_query_count(self):
        """
        3 queries (author + reviews prefetched):
        1) SELECT books
        2) SELECT authors WHERE id IN (…)  (VirtualAuthor prefetch)
        3) SELECT reviews WHERE book_id IN (…) (VirtualReview prefetch)
        """
        with self.assertNumQueries(3):
            response = self.client.get("/integration/books/virtual/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)

    def test_virtual_model_author_only_query_count(self):
        """
        2 queries (only author prefetched, reviews skipped):
        1) SELECT books
        2) SELECT authors WHERE id IN (…) (VirtualAuthor prefetch)

        VirtualModelSerializer's LookupFinder does not see the reviews
        field (stripped by DynamicSerializerView) so VirtualReview is
        never asked to hydrate the queryset.
        """
        with self.assertNumQueries(2):
            response = self.client.get("/integration/books/virtual-author/")
        self.assertEqual(response.status_code, 200)

    def test_virtual_model_flat_query_count(self):
        """
        1 query (no prefetches):
        1) SELECT books

        All nested serializers are stripped so LookupFinder only sees
        concrete fields — no prefetches are generated.
        """
        with self.assertNumQueries(1):
            response = self.client.get("/integration/books/virtual-flat/")
        self.assertEqual(response.status_code, 200)

    def test_virtual_model_detail_view_query_count(self):
        """
        3 queries (single-object retrieve, still prefetches):
        1) SELECT book WHERE id = X
        2) SELECT authors WHERE id IN (…) (VirtualAuthor prefetch)
        3) SELECT reviews WHERE book_id IN (…) (VirtualReview prefetch)
        """
        with self.assertNumQueries(3):
            response = self.client.get(
                f"/integration/books/virtual/{self.book1.pk}/"
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], self.book1.pk)

    def test_virtual_model_response_structure_with_all_nested(self):
        """Response from full-nested view contains author and reviews sub-objects."""
        response = self.client.get("/integration/books/virtual/")
        book = response.json()[0]
        self.assertEqual(
            set(book.keys()), {"id", "title", "author", "reviews"},
        )
        self.assertEqual(set(book["author"].keys()), {"id", "name"})
        self.assertTrue(len(book["reviews"]) >= 1)
        self.assertEqual(set(book["reviews"][0].keys()), {"id", "rating"})

    def test_virtual_model_response_structure_flat(self):
        """Response from flat view contains only id and title."""
        response = self.client.get("/integration/books/virtual-flat/")
        book = response.json()[0]
        self.assertEqual(set(book.keys()), {"id", "title"})

    def test_virtual_model_detail_response_structure(self):
        """Detail response contains all declared nested fields."""
        response = self.client.get(
            f"/integration/books/virtual/{self.book1.pk}/"
        )
        data = response.json()
        self.assertEqual(
            set(data.keys()), {"id", "title", "isbn", "author", "reviews"},
        )
        self.assertEqual(
            set(data["author"].keys()), {"id", "name", "birth_year"},
        )
        self.assertEqual(
            set(data["reviews"][0].keys()), {"id", "rating", "comment"},
        )

    def test_virtual_model_constant_query_count_with_more_data(self):
        """
        Query count stays at 3 regardless of data volume — prefetch_related
        batches all related objects per relation in a single query.
        """
        author3 = Author.objects.create(name="Author Gamma", birth_year=1995)
        book3 = Book.objects.create(
            title="Third Book", isbn="3333333333333",
            author=author3, library=self.library,
        )
        Review.objects.create(rating=1, comment="Poor", book=book3)

        with self.assertNumQueries(3):
            response = self.client.get("/integration/books/virtual/")
        self.assertEqual(len(response.json()), 3)
