Integration with django-virtual-models
=======================================

`django-virtual-models <https://github.com/vintasoftware/django-virtual-models>`_
is a library that automatically optimizes querysets based on which serializer
fields are present. When combined with ``django-dynamic-serializer``, the
prefetch strategy is driven entirely by your ``get_serializer_fields()``
declaration — relations that are stripped from the serializer are never
prefetched.


Why it matters
--------------

Without virtual models you must manually keep querysets and serializer fields in
sync. If a view only needs ``["id", "title"]`` but the queryset still calls
``prefetch_related("reviews")``, the database does extra work for data that is
never serialized.

With virtual models the queryset optimization is **automatic**: the library
inspects the serializer fields and generates only the necessary
``select_related`` / ``prefetch_related`` calls.


How the integration works
-------------------------

The integration relies on two hooks:

1. ``DynamicSerializerView._get_empty_serializer()`` creates a serializer
   instance with ``instance=None`` and the ``fields`` kwarg applied. This
   produces a serializer whose ``.fields`` dict contains **only** the fields
   declared in ``get_serializer_fields()``.

2. ``VirtualModelListAPIView.get_queryset()`` (from django-virtual-models) calls
   ``_get_empty_serializer()`` and passes the result to its ``LookupFinder``.
   The finder inspects the filtered fields and generates prefetch calls only for
   the relations that are still present.

The flow looks like this:

.. code-block:: text

   GET request
     -> DynamicSerializerView._get_empty_serializer()
       -> creates serializer with field selection applied
     -> VirtualModelListAPIView.get_queryset()
       -> LookupFinder inspects filtered serializer.fields
       -> generates only the needed prefetch_related() calls
     -> queryset is evaluated with minimal queries


Setup
-----

Step 1: Install the dependency
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   pip install django-virtual-models>=0.1.4

Step 2: Define virtual models
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create a virtual model for each related model. The virtual model tells
django-virtual-models how to prefetch the relation:

.. code-block:: python

   import django_virtual_models as v

   from .models import Author, Book, Review


   class VirtualAuthor(v.VirtualModel):
       class Meta:
           model = Author


   class VirtualReview(v.VirtualModel):
       class Meta:
           model = Review


   class VirtualBook(v.VirtualModel):
       author = VirtualAuthor()
       review_list = VirtualReview(lookup="reviews")

       class Meta:
           model = Book

``VirtualBook.author`` tells the library to prefetch the ``author`` FK.
``review_list`` uses ``lookup="reviews"`` to prefetch the reverse FK into a
``to_attr="review_list"`` attribute, avoiding a conflict with Book's default
``reviews`` related manager.

Step 3: Create serializers with VirtualModelSerializer
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Replace ``ModelSerializer`` with ``VirtualModelSerializer`` and point
``Meta.virtual_model`` to the corresponding virtual model:

.. code-block:: python

   from django_virtual_models.serializers import VirtualModelSerializer
   from django_dynamic_serializer import DynamicSerializerFieldsMixin


   class AuthorVirtualSerializer(DynamicSerializerFieldsMixin, VirtualModelSerializer):
       class Meta:
           model = Author
           fields = ["id", "name", "birth_year"]
           virtual_model = VirtualAuthor


   class ReviewVirtualSerializer(DynamicSerializerFieldsMixin, VirtualModelSerializer):
       class Meta:
           model = Review
           fields = ["id", "rating", "comment"]
           virtual_model = VirtualReview


   class BookVirtualSerializer(DynamicSerializerFieldsMixin, VirtualModelSerializer):
       author = AuthorVirtualSerializer()
       reviews = ReviewVirtualSerializer(source="review_list", many=True)

       class Meta:
           model = Book
           fields = ["id", "title", "isbn", "author", "reviews"]
           virtual_model = VirtualBook

Note ``source="review_list"`` on the ``reviews`` field — this reads from the
``to_attr`` set by the virtual model prefetch.

Step 4: Create views
^^^^^^^^^^^^^^^^^^^^

Combine ``DynamicSerializerView`` with ``VirtualModelListAPIView`` (or
``VirtualModelRetrieveAPIView``). You do **not** need to write a custom
``get_queryset()`` — the virtual model layer handles it automatically:

.. code-block:: python

   from django_virtual_models.generic_views import VirtualModelListAPIView
   from django_dynamic_serializer import DynamicSerializerView


   class BookVirtualModelListView(DynamicSerializerView, VirtualModelListAPIView):
       serializer_class = BookVirtualSerializer
       queryset = Book.objects.all()

       def get_serializer_fields(self):
           return [
               "id",
               "title",
               {"object_name": "author", "fields": ["id", "name"]},
               {"object_name": "reviews", "fields": ["id", "rating"]},
           ]

The queryset starts as a plain ``Book.objects.all()``. The virtual model layer
inspects the field-filtered serializer and adds the necessary prefetches before
evaluation.


Performance comparison
----------------------

The following table shows query counts for different field selections, all using
the same ``BookVirtualSerializer`` and ``VirtualModelListAPIView``:

.. list-table::
   :header-rows: 1
   :widths: 50 15 35

   * - Fields requested
     - Queries
     - What happens
   * - ``id``, ``title``, ``author``, ``reviews``
     - 3
     - 1 query for books + 1 for authors (prefetch) + 1 for reviews (prefetch)
   * - ``id``, ``title``, ``author``
     - 2
     - 1 query for books + 1 for authors (prefetch); reviews skipped
   * - ``id``, ``title``
     - 1
     - 1 query for books only (no prefetches)

The key insight: **query count scales with the number of requested relations, not
with the number of rows**. Adding more books does not increase the query count
because ``prefetch_related`` batches all related objects in a single query per
relation.

.. note::

   ``django-virtual-models`` uses ``prefetch_related`` for **all** relations,
   including forward ForeignKey fields like ``Book.author``. In plain Django you
   would use ``select_related("author")`` to fetch the author via a JOIN in the
   same query as books (1 query instead of 2). The trade-off is that virtual
   models give you **automatic** optimization driven by serializer fields,
   whereas ``select_related`` / ``prefetch_related`` must be maintained manually.

   For comparison, without virtual models:

   .. list-table::
      :header-rows: 1
      :widths: 50 25 25

      * - Fields requested
        - Manual optimization
        - Virtual models
      * - ``id``, ``title``, ``author``, ``reviews``
        - 2 queries (JOIN + prefetch)
        - 3 queries (prefetch + prefetch)
      * - ``id``, ``title``, ``author``
        - 1 query (JOIN)
        - 2 queries (prefetch)
      * - ``id``, ``title``
        - 1 query
        - 1 query

   Manual optimization uses ``select_related("author")`` for the FK (JOIN) and
   ``prefetch_related("reviews")`` for the reverse FK. Virtual models use
   ``prefetch_related`` for both, resulting in one extra query when the author
   relation is included. The benefit is that you do not need to write or update
   querysets when the field selection changes.

Without virtual models you would need to manually write a different queryset for
each view to achieve the same result. With this integration the optimization is
automatic — just change ``get_serializer_fields()`` and the queryset adapts.


Retrieve views
--------------

The same pattern works for single-object endpoints using
``VirtualModelRetrieveAPIView``:

.. code-block:: python

   from django_virtual_models.generic_views import VirtualModelRetrieveAPIView


   class BookVirtualModelDetailView(DynamicSerializerView, VirtualModelRetrieveAPIView):
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

This executes 3 queries (1 for the book + 1 for authors prefetch + 1 for
reviews prefetch) regardless of how many reviews exist.
