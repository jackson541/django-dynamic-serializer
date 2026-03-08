from rest_framework.serializers import ListSerializer


class DynamicSerializerFieldsMixin:
    """
    Mixin for dynamically selecting which serializer fields to include in the response.

    By restricting serialization to only the requested fields, this mixin also improves
    database performance when combined with ``only()`` or ``defer()`` on your queryset,
    since unrequested related objects won't be serialized or fetched.

    Pass a ``fields`` argument when instantiating the serializer to declare exactly
    which fields should be present. The format is a list where plain strings represent
    top-level fields and dicts describe nested serializers::

        fields = [
            'id',
            'worker',
            {
                'object_name': 'job',
                'fields': [
                    'id',
                    'worker_amount',
                    {
                        'object_name': 'establishment',
                        'fields': ['id', 'rating'],
                    }
                ]
            }
        ]

    Nested serializer entries must always contain the keys ``object_name``
    (matching the serializer field name) and ``fields``.
    """

    def __init__(self, *args, **kwargs):
        fields = kwargs.pop('fields', None)

        super().__init__(*args, **kwargs)

        if fields is not None:
            self._apply_field_selection(self.fields, fields)

    def _apply_field_selection(self, current_field, requested_fields):
        if isinstance(current_field, ListSerializer):
            current_field = current_field.child

        requested_names = []

        for field in requested_fields:
            if isinstance(field, str):
                requested_names.append(field)
                continue

            field_name = field['object_name']
            requested_names.append(field_name)
            self._apply_field_selection(current_field.fields[field_name], field['fields'])

        requested_set = set(requested_names)
        for field_name in set(current_field.fields) - requested_set:
            current_field.fields.pop(field_name)
