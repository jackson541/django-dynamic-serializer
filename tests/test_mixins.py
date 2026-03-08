"""
Unit tests for DynamicSerializerFieldsMixin.

Verifies that the mixin correctly filters serializer fields when the
``fields`` kwarg is passed, including flat, nested, and deeply nested
field specifications, and when used with many=True (ListSerializer).
"""
from django.test import TestCase

from .models import Author, Book, Library, Review
from .serializers import AuthorSerializer, BookSerializer, LibrarySerializer


class DynamicSerializerFieldsMixinTest(TestCase):
    """Unit tests for DynamicSerializerFieldsMixin field selection behavior."""

    def test_no_fields_kwarg_returns_all_fields(self):
        """Without a ``fields`` kwarg, the serializer keeps every declared field."""
        serializer = BookSerializer()
        self.assertEqual(
            set(serializer.fields.keys()),
            {"id", "title", "isbn", "author", "reviews"},
        )

    def test_flat_fields_filters_top_level(self):
        """Passing flat field names keeps only those top-level fields."""
        serializer = BookSerializer(fields=["id", "title"])
        self.assertEqual(set(serializer.fields.keys()), {"id", "title"})

    def test_nested_fields_filters_child_serializer(self):
        """Nested dict with object_name and fields filters the child serializer."""
        serializer = BookSerializer(
            fields=[
                "id",
                "title",
                {"object_name": "author", "fields": ["id"]},
            ]
        )
        self.assertEqual(set(serializer.fields.keys()), {"id", "title", "author"})
        self.assertEqual(set(serializer.fields["author"].fields.keys()), {"id"})

    def test_deeply_nested_fields(self):
        """Three-level nesting (Library -> books -> author) filters at each level."""
        serializer = LibrarySerializer(
            fields=[
                "id",
                "name",
                {
                    "object_name": "books",
                    "fields": [
                        "id",
                        {"object_name": "author", "fields": ["name"]},
                    ],
                },
            ]
        )
        self.assertEqual(set(serializer.fields.keys()), {"id", "name", "books"})

        book_fields = serializer.fields["books"].child.fields
        self.assertEqual(set(book_fields.keys()), {"id", "author"})
        self.assertEqual(set(book_fields["author"].fields.keys()), {"name"})

    def test_many_true_list_serializer(self):
        """With many=True, field selection applies to the ListSerializer child."""
        serializer = BookSerializer(many=True, fields=["id", "isbn"])
        child_fields = serializer.child.fields
        self.assertEqual(set(child_fields.keys()), {"id", "isbn"})

    def test_empty_fields_removes_all(self):
        """An empty ``fields`` list results in zero fields on the serializer."""
        serializer = BookSerializer(fields=[])
        self.assertEqual(len(serializer.fields), 0)
