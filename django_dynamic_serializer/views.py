class DynamicSerializerView:
    """
    View mixin that passes dynamic field selection to the serializer.

    Subclasses must implement ``get_serializer_fields()`` to return the field
    specification list. On GET requests the fields are forwarded to the
    serializer so that only the declared fields are included in the response.

    The method `_get_empty_serializer` is used when integration with virtual models library.
    """

    def _get_empty_serializer(self):
        serializer_class = self.get_serializer_class()
        kwargs = {"context": self.get_serializer_context()}

        if self.request.method == 'GET':
            serializer = serializer_class(
                instance=None,
                fields=self.get_serializer_fields(),
                **kwargs,
            )
        else:
            serializer = serializer_class(instance=None, **kwargs)

        return serializer

    def get_serializer_fields(self):
        raise NotImplementedError(
            "Subclasses must implement get_serializer_fields() "
            "returning the list of fields to include."
        )

    def get_serializer(self, *args, **kwargs):
        if self.request.method == 'GET':
            serializer = super().get_serializer(
                *args,
                fields=self.get_serializer_fields(),
                **kwargs,
            )
        else:
            serializer = super().get_serializer(*args, **kwargs)

        return serializer
