"""
Test serializers using DynamicSerializerFieldsMixin.

Includes two families:
- Explicit field lists: ReviewSerializer, AuthorSerializer, BookSerializer,
  LibrarySerializer.
- ``__all__`` variants: ReviewAllFieldsSerializer, AuthorAllFieldsSerializer,
  BookAllFieldsSerializer, LibraryAllFieldsSerializer.

BookWriteSerializer is a plain ModelSerializer for create (no dynamic fields).
"""
from rest_framework import serializers

from django_dynamic_serializer import DynamicSerializerFieldsMixin

from .models import Author, Book, Library, Review


# ---------------------------------------------------------------------------
# Serializers with explicit field lists
# ---------------------------------------------------------------------------

class ReviewSerializer(DynamicSerializerFieldsMixin, serializers.ModelSerializer):
    """Flat serializer for Review (id, rating, comment)."""

    class Meta:
        model = Review
        fields = ["id", "rating", "comment"]


class AuthorSerializer(DynamicSerializerFieldsMixin, serializers.ModelSerializer):
    """Flat serializer for Author (id, name, birth_year)."""

    class Meta:
        model = Author
        fields = ["id", "name", "birth_year"]


class BookSerializer(DynamicSerializerFieldsMixin, serializers.ModelSerializer):
    """Book with nested author and reviews; supports dynamic field selection."""

    author = AuthorSerializer()
    reviews = ReviewSerializer(many=True)

    class Meta:
        model = Book
        fields = ["id", "title", "isbn", "author", "reviews"]


class BookWriteSerializer(serializers.ModelSerializer):
    """Plain ModelSerializer for creating books (no dynamic fields)."""

    class Meta:
        model = Book
        fields = ["id", "title", "isbn", "author", "library"]


class LibrarySerializer(DynamicSerializerFieldsMixin, serializers.ModelSerializer):
    """Library with nested books (each book can nest author/reviews)."""

    books = BookSerializer(many=True)

    class Meta:
        model = Library
        fields = ["id", "name", "city", "books"]


# ---------------------------------------------------------------------------
# Serializers using fields = "__all__"
# ---------------------------------------------------------------------------

class ReviewAllFieldsSerializer(DynamicSerializerFieldsMixin, serializers.ModelSerializer):
    """Review with ``fields = '__all__'``; exposes id, rating, comment, book."""

    class Meta:
        model = Review
        fields = "__all__"


class AuthorAllFieldsSerializer(DynamicSerializerFieldsMixin, serializers.ModelSerializer):
    """Author with ``fields = '__all__'``; exposes id, name, birth_year."""

    class Meta:
        model = Author
        fields = "__all__"


class BookAllFieldsSerializer(DynamicSerializerFieldsMixin, serializers.ModelSerializer):
    """Book with ``fields = '__all__'`` and nested author/reviews."""

    author = AuthorAllFieldsSerializer()
    reviews = ReviewAllFieldsSerializer(many=True)

    class Meta:
        model = Book
        fields = "__all__"


class LibraryAllFieldsSerializer(DynamicSerializerFieldsMixin, serializers.ModelSerializer):
    """Library with ``fields = '__all__'`` and nested books."""

    books = BookAllFieldsSerializer(many=True)

    class Meta:
        model = Library
        fields = "__all__"


# ---------------------------------------------------------------------------
# Serializers for django-virtual-models integration
# ---------------------------------------------------------------------------

from .virtual_models import HAS_VIRTUAL_MODELS

if HAS_VIRTUAL_MODELS:
    from django_virtual_models.serializers import VirtualModelSerializer

    from .virtual_models import VirtualAuthor, VirtualBook, VirtualReview

    class AuthorVirtualSerializer(DynamicSerializerFieldsMixin, VirtualModelSerializer):
        """Author serializer backed by VirtualAuthor for auto-prefetch resolution."""

        class Meta:
            model = Author
            fields = ["id", "name", "birth_year"]
            virtual_model = VirtualAuthor

    class ReviewVirtualSerializer(DynamicSerializerFieldsMixin, VirtualModelSerializer):
        """Review serializer backed by VirtualReview for auto-prefetch resolution."""

        class Meta:
            model = Review
            fields = ["id", "rating", "comment"]
            virtual_model = VirtualReview

    class BookVirtualSerializer(DynamicSerializerFieldsMixin, VirtualModelSerializer):
        """
        Book serializer backed by VirtualBook.

        ``reviews`` uses ``source='review_list'`` to read from the
        ``to_attr`` set by VirtualReview(lookup='reviews') on VirtualBook,
        avoiding a conflict with Book's ``reviews`` RelatedManager.
        """
        author = AuthorVirtualSerializer()
        reviews = ReviewVirtualSerializer(source="review_list", many=True)

        class Meta:
            model = Book
            fields = ["id", "title", "isbn", "author", "reviews"]
            virtual_model = VirtualBook
