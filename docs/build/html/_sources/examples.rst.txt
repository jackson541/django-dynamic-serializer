Usage Examples
==============

This page walks through common usage patterns, from defining serializers to
pairing them with views and queryset optimizations.


Defining serializers
--------------------

Add ``DynamicSerializerFieldsMixin`` as the **first** parent of every serializer
that should support dynamic field selection. Nested serializers must also use the
mixin so that recursive field filtering works at every level.

.. code-block:: python

   from rest_framework import serializers
   from django_dynamic_serializer import DynamicSerializerFieldsMixin


   class ReviewSerializer(DynamicSerializerFieldsMixin, serializers.ModelSerializer):
       class Meta:
           model = Review
           fields = ["id", "rating", "comment"]


   class AuthorSerializer(DynamicSerializerFieldsMixin, serializers.ModelSerializer):
       class Meta:
           model = Author
           fields = ["id", "name", "birth_year"]


   class BookSerializer(DynamicSerializerFieldsMixin, serializers.ModelSerializer):
       author = AuthorSerializer()
       reviews = ReviewSerializer(many=True)

       class Meta:
           model = Book
           fields = ["id", "title", "isbn", "author", "reviews"]

The mixin also works with serializers that use ``fields = "__all__"``:

.. code-block:: python

   class BookAllFieldsSerializer(DynamicSerializerFieldsMixin, serializers.ModelSerializer):
       author = AuthorAllFieldsSerializer()
       reviews = ReviewAllFieldsSerializer(many=True)

       class Meta:
           model = Book
           fields = "__all__"


Using the serializer directly
-----------------------------

You do not need a view to use dynamic field selection. Pass the ``fields``
keyword argument when instantiating any serializer that includes the mixin.

Flat fields only
^^^^^^^^^^^^^^^^

Request only scalar fields to skip all related-object access:

.. code-block:: python

   qs = Book.objects.only("id", "title")

   serializer = BookSerializer(qs, many=True, fields=["id", "title"])
   serializer.data
   # Each item contains only {"id": ..., "title": ...}

Because ``author`` and ``reviews`` are stripped from the serializer, Django never
accesses those relations — the single ``SELECT id, title FROM book`` is the only
query executed.

Nested field selection
^^^^^^^^^^^^^^^^^^^^^^

Include a related object while choosing exactly which of its fields to serialize:

.. code-block:: python

   qs = Book.objects.select_related("author")

   serializer = BookSerializer(
       qs,
       many=True,
       fields=[
           "id",
           "title",
           {"object_name": "author", "fields": ["id", "name"]},
       ],
   )
   serializer.data
   # author.birth_year is excluded from the output

Only one query is needed (books JOIN author) because ``reviews`` is not in the
field list and is therefore never accessed.


Using with views
----------------

``DynamicSerializerView`` injects the field specification automatically on every
GET request. Combine it with any DRF generic view.

List view
^^^^^^^^^

.. code-block:: python

   from rest_framework.generics import ListAPIView
   from django_dynamic_serializer import DynamicSerializerView


   class BookListView(DynamicSerializerView, ListAPIView):
       serializer_class = BookSerializer
       queryset = Book.objects.select_related("author")

       def get_serializer_fields(self):
           return [
               "id",
               "title",
               {"object_name": "author", "fields": ["id", "name"]},
           ]

The response only contains ``id``, ``title``, and the nested ``author`` with
``id`` and ``name``. All other fields (``isbn``, ``reviews``,
``author.birth_year``) are excluded.

Detail view
^^^^^^^^^^^

.. code-block:: python

   from rest_framework.generics import RetrieveAPIView


   class BookDetailView(DynamicSerializerView, RetrieveAPIView):
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

Here the detail endpoint returns more fields than the list view, including
``isbn`` and the full ``reviews`` list. The queryset is optimized with both
``select_related`` and ``prefetch_related`` to match.

Flat-only view
^^^^^^^^^^^^^^

When a view only needs scalar fields, the queryset requires no joins at all:

.. code-block:: python

   class BookFlatListView(DynamicSerializerView, ListAPIView):
       serializer_class = BookSerializer
       queryset = Book.objects.all()

       def get_serializer_fields(self):
           return ["id", "title"]

Write operations are unaffected
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Field selection applies only to GET requests. POST, PUT, and PATCH use the full
serializer automatically:

.. code-block:: python

   from rest_framework.generics import CreateAPIView


   class BookCreateView(CreateAPIView):
       serializer_class = BookWriteSerializer
       queryset = Book.objects.all()


Deep nesting
------------

The field specification supports arbitrary nesting depth. Here is a three-level
example: Library -> Books -> Author + Reviews.

.. code-block:: python

   from django.db.models import Prefetch


   class LibraryOptimizedListView(DynamicSerializerView, ListAPIView):
       serializer_class = LibrarySerializer

       def get_queryset(self):
           return Library.objects.prefetch_related(
               Prefetch(
                   "books",
                   queryset=Book.objects.select_related("author").prefetch_related("reviews"),
               )
           )

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

With this setup the view executes exactly **3 queries** regardless of how many
libraries, books, or reviews exist:

1. ``SELECT`` libraries
2. ``SELECT`` books ``JOIN`` author ``WHERE library_id IN (...)`` (prefetch + select_related)
3. ``SELECT`` reviews ``WHERE book_id IN (...)`` (prefetch)


Partial field selection on the same queryset
--------------------------------------------

You can reuse the same optimized queryset and simply request fewer fields. The
dynamic field selection reduces the response payload; **the queryset still executes
the same prefetches, pay attention to get on database only the fields you are requesting**:

.. code-block:: python

   class LibraryOptimizedPartialListView(DynamicSerializerView, ListAPIView):
       serializer_class = LibrarySerializer

       def get_queryset(self):
           return Library.objects.prefetch_related(
               Prefetch(
                   "books",
                   queryset=Book.objects.select_related("author").prefetch_related("reviews"),
               )
           )

       def get_serializer_fields(self):
           return [
               "id",
               "name",
               {
                   "object_name": "books",
                   "fields": ["id", "title"],
               },
           ]

The response now only contains ``id`` and ``name`` on each library, and ``id``
and ``title`` on each book — author and reviews are stripped entirely.


Avoiding N+1 with flat fields
------------------------------

Dynamic field selection can avoid the N+1 problem even when the queryset has no
optimization. If a view only declares flat fields, nested serializers are removed
entirely and their related-object lookups are never triggered:

.. code-block:: python

   class LibraryUnoptimizedFlatListView(DynamicSerializerView, ListAPIView):
       serializer_class = LibrarySerializer
       queryset = Library.objects.all()

       def get_serializer_fields(self):
           return ["id", "name"]

This executes a single ``SELECT`` on the library table. Even though
``LibrarySerializer`` declares a nested ``books`` field, it is stripped before
serialization, so ``books.all()`` is never accessed.
