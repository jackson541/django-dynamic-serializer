API Reference
=============

The library exposes two public classes, both importable from the top-level
package:

.. code-block:: python

   from django_dynamic_serializer import (
       DynamicSerializerFieldsMixin,
       DynamicSerializerView,
   )


``DynamicSerializerFieldsMixin``
--------------------------------

**Module:** ``django_dynamic_serializer.mixins``

A serializer mixin that accepts an optional ``fields`` keyword argument to
dynamically select which fields are included in the serialized output. Add it to
any ``ModelSerializer`` (or any ``Serializer`` subclass) as the **first** parent
class so its ``__init__`` runs before the DRF base class.

.. code-block:: python

   from rest_framework import serializers
   from django_dynamic_serializer import DynamicSerializerFieldsMixin


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

Field specification format
^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``fields`` argument is a list where each entry is either:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Entry type
     - Meaning
   * - ``"field_name"``
     - Include a top-level field as-is.
   * - ``{"object_name": "nested", "fields": [...]}``
     - Include a nested serializer and recursively select its sub-fields.

Example:

.. code-block:: python

   fields = [
       "id",
       "title",
       {
           "object_name": "author",
           "fields": ["id", "name"],
       },
   ]

Nesting can go as deep as your serializer hierarchy requires:

.. code-block:: python

   fields = [
       "id",
       "name",
       {
           "object_name": "books",
           "fields": [
               "id",
               "title",
               {"object_name": "author", "fields": ["name"]},
           ],
       },
   ]

How it works
^^^^^^^^^^^^

1. ``__init__`` pops the ``fields`` kwarg before calling ``super().__init__()``
   so that DRF's ``Serializer.__init__`` does not receive an unexpected argument.

2. After the parent ``__init__`` has built the full ``self.fields`` ordered dict,
   ``_apply_field_selection`` is called to prune it.

3. ``_apply_field_selection`` walks the requested field list. For each nested
   dict entry it recurses into the child serializer's ``.fields``. After
   processing all entries, any field **not** in the requested set is removed from
   the serializer.

4. When a field wraps a ``many=True`` serializer, DRF represents it as a
   ``ListSerializer``. The method transparently unwraps to
   ``ListSerializer.child`` before applying the selection.


``DynamicSerializerView``
-------------------------

**Module:** ``django_dynamic_serializer.views``

A view mixin that connects the field specification to the serializer. Combine it
with any DRF generic view (``ListAPIView``, ``RetrieveAPIView``, etc.) as the
**first** parent class.

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

``get_serializer_fields()``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Subclasses **must** implement this method. It returns the field specification list
(same format accepted by ``DynamicSerializerFieldsMixin``). If not implemented,
a ``NotImplementedError`` is raised at request time.

``get_serializer()``
^^^^^^^^^^^^^^^^^^^^

Overrides DRF's ``get_serializer()`` to inject the ``fields`` kwarg on **GET**
requests. For non-GET methods (POST, PUT, PATCH, DELETE) the serializer is
created normally with all fields, so write operations are unaffected.

``_get_empty_serializer()``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Creates a field-filtered serializer instance with ``instance=None``. This hook
exists specifically for the **django-virtual-models** integration: the
``VirtualModelListAPIView`` calls ``_get_empty_serializer()`` to inspect which
fields are present, then generates only the needed ``prefetch_related`` calls.
See :doc:`virtual_models` for details.

On non-GET requests this method returns a plain serializer (no field filtering)
so that introspection used by virtual models does not interfere with write
operations.
