"""
Test domain models for the Library app.

Library, Author, Book, and Review provide a three-level nesting structure
(Library -> Book -> Author / Review) used to exercise dynamic serializer
field selection and query optimization.
"""
from django.db import models


class Library(models.Model):
    """A library that holds books."""

    name = models.CharField(max_length=200)
    city = models.CharField(max_length=100)

    class Meta:
        app_label = "tests"


class Author(models.Model):
    """Author of one or more books."""

    name = models.CharField(max_length=200)
    birth_year = models.IntegerField()

    class Meta:
        app_label = "tests"


class Book(models.Model):
    """Book with one author, one library, and many reviews."""

    title = models.CharField(max_length=300)
    isbn = models.CharField(max_length=13)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="books")
    library = models.ForeignKey(Library, on_delete=models.CASCADE, related_name="books")

    class Meta:
        app_label = "tests"


class Review(models.Model):
    """Review (rating and comment) for a book."""

    rating = models.IntegerField()
    comment = models.TextField()
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="reviews")

    class Meta:
        app_label = "tests"
