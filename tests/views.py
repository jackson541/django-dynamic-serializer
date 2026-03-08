"""
Test views using DynamicSerializerView.

List/detail views declare get_serializer_fields(); create view does not
use dynamic fields. MissingFieldsView is used to test NotImplementedError.
Integration views exercise optimized, unoptimized, __all__, and virtual-model
scenarios at the Library and Book depth levels.
"""
from django.db.models import Prefetch
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView

from django_dynamic_serializer import DynamicSerializerView

from .models import Book, Library
from .serializers import (
    BookSerializer,
    BookWriteSerializer,
    LibraryAllFieldsSerializer,
    LibrarySerializer,
)


# ---------------------------------------------------------------------------
# Original views (used by existing unit / response tests)
# ---------------------------------------------------------------------------

class BookListView(DynamicSerializerView, ListAPIView):
    """List books with id, title, and nested author (id, name) only."""

    serializer_class = BookSerializer
    queryset = Book.objects.select_related("author")

    def get_serializer_fields(self):
        return [
            "id",
            "title",
            {"object_name": "author", "fields": ["id", "name"]},
        ]


class BookDetailView(DynamicSerializerView, RetrieveAPIView):
    """Retrieve a single book with full author and reviews (all sub-fields)."""

    serializer_class = BookSerializer
    queryset = Book.objects.select_related("author").prefetch_related("reviews")

    def get_serializer_fields(self):
        return [
            "id",
            "title",
            "isbn",
            {"object_name": "author", "fields": ["id", "name", "birth_year"]},
            {"object_name": "reviews", "fields": ["id", "rating", "comment"]},
        ]


class BookCreateView(CreateAPIView):
    """Create a book; uses full serializer (no dynamic field selection)."""

    serializer_class = BookWriteSerializer
    queryset = Book.objects.all()


class BookFlatListView(DynamicSerializerView, ListAPIView):
    """Returns only flat (non-nested) fields."""

    serializer_class = BookSerializer
    queryset = Book.objects.all()

    def get_serializer_fields(self):
        return ["id", "title"]


class MissingFieldsView(DynamicSerializerView, ListAPIView):
    """View that does NOT implement get_serializer_fields(); used to test NotImplementedError."""

    serializer_class = BookSerializer
    queryset = Book.objects.all()


# ---------------------------------------------------------------------------
# Integration views — optimized (select_related + prefetch_related)
# ---------------------------------------------------------------------------

def _optimized_library_queryset():
    return Library.objects.prefetch_related(
        Prefetch(
            "books",
            queryset=Book.objects.select_related("author").prefetch_related("reviews"),
        )
    )


class LibraryOptimizedListView(DynamicSerializerView, ListAPIView):
    """Full-depth optimized: Library -> Books -> Author + Reviews."""

    serializer_class = LibrarySerializer

    def get_queryset(self):
        return _optimized_library_queryset()

    def get_serializer_fields(self):
        return [
            "id",
            "name",
            "city",
            {
                "object_name": "books",
                "fields": [
                    "id",
                    "title",
                    "isbn",
                    {"object_name": "author", "fields": ["id", "name", "birth_year"]},
                    {"object_name": "reviews", "fields": ["id", "rating", "comment"]},
                ],
            },
        ]


class LibraryOptimizedPartialListView(DynamicSerializerView, ListAPIView):
    """Same optimized queryset but only Library id/name and Book id/title."""

    serializer_class = LibrarySerializer

    def get_queryset(self):
        return _optimized_library_queryset()

    def get_serializer_fields(self):
        return [
            "id",
            "name",
            {
                "object_name": "books",
                "fields": ["id", "title"],
            },
        ]


# ---------------------------------------------------------------------------
# Integration views — unoptimized (N+1)
# ---------------------------------------------------------------------------

class LibraryUnoptimizedListView(DynamicSerializerView, ListAPIView):
    """No optimization: Library.objects.all() with full nested fields (N+1)."""

    serializer_class = LibrarySerializer
    queryset = Library.objects.all()

    def get_serializer_fields(self):
        return [
            "id",
            "name",
            {
                "object_name": "books",
                "fields": [
                    "id",
                    "title",
                    {"object_name": "author", "fields": ["id", "name"]},
                    {"object_name": "reviews", "fields": ["id", "rating"]},
                ],
            },
        ]


class LibraryUnoptimizedFlatListView(DynamicSerializerView, ListAPIView):
    """No optimization but flat fields only — avoids N+1 via dynamic fields."""

    serializer_class = LibrarySerializer
    queryset = Library.objects.all()

    def get_serializer_fields(self):
        return ["id", "name"]


# ---------------------------------------------------------------------------
# Integration views — __all__ serializers
# ---------------------------------------------------------------------------

class LibraryAllFieldsListView(DynamicSerializerView, ListAPIView):
    """Uses __all__ serializers with optimized queryset + dynamic field selection."""

    serializer_class = LibraryAllFieldsSerializer

    def get_queryset(self):
        return _optimized_library_queryset()

    def get_serializer_fields(self):
        return [
            "id",
            "name",
            {
                "object_name": "books",
                "fields": [
                    "id",
                    "title",
                    {"object_name": "author", "fields": ["id", "name"]},
                ],
            },
        ]


# ---------------------------------------------------------------------------
# Integration views — django-virtual-models
# (Uses VirtualModelListAPIView / VirtualModelRetrieveAPIView so
#  get_queryset() is automatically optimized via _get_empty_serializer.)
# ---------------------------------------------------------------------------

from .virtual_models import HAS_VIRTUAL_MODELS

if HAS_VIRTUAL_MODELS:
    from django_virtual_models.generic_views import (
        VirtualModelListAPIView,
        VirtualModelRetrieveAPIView,
    )

    from .serializers import BookVirtualSerializer

    class BookVirtualModelListView(DynamicSerializerView, VirtualModelListAPIView):
        """
        List books using VirtualModelListAPIView.

        get_queryset() is handled by GenericVirtualModelViewMixin: it
        calls _get_empty_serializer() (overridden by DynamicSerializerView
        to apply field selection), then asks VirtualModelSerializer to
        compute the optimized queryset. Only the relations present in the
        filtered serializer are prefetched.
        """
        serializer_class = BookVirtualSerializer
        queryset = Book.objects.all()

        def get_serializer_fields(self):
            return [
                "id",
                "title",
                {"object_name": "author", "fields": ["id", "name"]},
                {"object_name": "reviews", "fields": ["id", "rating"]},
            ]

    class BookVirtualModelFlatListView(DynamicSerializerView, VirtualModelListAPIView):
        """
        List books with flat fields only via VirtualModelListAPIView.

        Since only flat fields are declared, _get_empty_serializer strips
        nested serializers, and the LookupFinder generates no prefetches.
        """
        serializer_class = BookVirtualSerializer
        queryset = Book.objects.all()

        def get_serializer_fields(self):
            return ["id", "title"]

    class BookVirtualModelAuthorOnlyListView(DynamicSerializerView, VirtualModelListAPIView):
        """
        List books requesting author but NOT reviews.

        VirtualModelSerializer skips the reviews prefetch because the
        reviews field is stripped by DynamicSerializerView.
        """
        serializer_class = BookVirtualSerializer
        queryset = Book.objects.all()

        def get_serializer_fields(self):
            return [
                "id",
                "title",
                {"object_name": "author", "fields": ["id", "name"]},
            ]

    class BookVirtualModelDetailView(DynamicSerializerView, VirtualModelRetrieveAPIView):
        """
        Retrieve a single book using VirtualModelRetrieveAPIView.

        Full nested fields: author and reviews are both prefetched.
        """
        serializer_class = BookVirtualSerializer
        queryset = Book.objects.all()

        def get_serializer_fields(self):
            return [
                "id",
                "title",
                "isbn",
                {"object_name": "author", "fields": ["id", "name", "birth_year"]},
                {"object_name": "reviews", "fields": ["id", "rating", "comment"]},
            ]
