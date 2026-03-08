django-dynamic-serializer
=========================

Dynamically select which fields a Django REST Framework serializer returns per
view, without duplicating serializer classes or over-fetching from the database.


The problem without this library
-------------------------------

**Repeated serializers with similar fields.** It is common to need different
field sets for the same model: a list endpoint might return only ``id``,
``title``, and a minimal nested ``author`` (``id``, ``name``), while a detail
endpoint returns full ``author`` and ``reviews``. Without dynamic field
selection you end up maintaining multiple serializers that differ only in
``Meta.fields`` or nested declarations — e.g. ``BookListSerializer``,
``BookDetailSerializer``, ``BookMinimalSerializer`` — and keeping them in sync
when the model or API contract changes.

.. code-block:: python

   # Same model, three serializers to maintain
   class BookListSerializer(serializers.ModelSerializer):
       author = AuthorMinimalSerializer()
       class Meta:
           model = Book
           fields = ["id", "title", "author"]

   class BookDetailSerializer(serializers.ModelSerializer):
       author = AuthorSerializer()
       reviews = ReviewSerializer(many=True)
       class Meta:
           model = Book
           fields = ["id", "title", "isbn", "author", "reviews"]

   class BookMinimalSerializer(serializers.ModelSerializer):
       class Meta:
           model = Book
           fields = ["id", "title"]

**Database performance with “fat” serializers.** When a single serializer
declares many relations (e.g. ``author``, ``reviews``, ``category``), every view
that uses it may trigger prefetches for all of them, even when the view only
needs a subset. That leads to unnecessary queries and larger result sets. If you
strip fields only in the response (e.g. with a custom ``to_representation``),
Django has already executed the joins and prefetches for data you never use.

.. code-block:: python

   # List view only needs id/title, but the serializer pulls in everything
   class BookListView(ListAPIView):
       serializer_class = BookSerializer  # has author, reviews, isbn, ...
       queryset = Book.objects.select_related("author").prefetch_related("reviews")
       # ^ Two extra queries and JOINs even though list response omits them

   # Or you hide fields in to_representation — but DB work is already done
   def to_representation(self, instance):
       data = super().to_representation(instance)
       if self.context.get("view").action == "list":
           return {k: data[k] for k in ("id", "title")}
       return data
   # Django still ran select_related/prefetch_related; you just threw the data away


What this library does
----------------------

You define **one** serializer with all possible fields and nested relations. Each
view declares exactly which fields it needs via ``get_serializer_fields()``. The
library prunes the serializer’s field set before serialization, so:

* **Smaller payloads** — only the declared fields appear in the response.
* **Fewer queries** — relations that are not in the field set are never
  accessed, so you can align your queryset (e.g. ``select_related``,
  ``prefetch_related``, ``only()``) with what the view actually serializes.
* **No serializer duplication** — one serializer class, many field shapes.

Combined with optional **django-virtual-models**, the queryset can be optimized
automatically from the same field declaration (see :doc:`virtual_models`).


Quick example
-------------

.. code-block:: python

   class BookListView(DynamicSerializerView, ListAPIView):
       serializer_class = BookSerializer
       queryset = Book.objects.select_related("author")

       def get_serializer_fields(self):
           return [
               "id",
               "title",
               {"object_name": "author", "fields": ["id", "name"]},
           ]

Only ``id``, ``title``, and nested ``author`` with ``id`` and ``name`` appear
in the response; ``isbn`` and ``reviews`` are omitted. Because they are not in
the field set, you can avoid prefetching ``reviews`` for this view entirely.

.. toctree::
   :maxdepth: 2
   :caption: Contents

   installation
   api
   examples
   virtual_models


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
