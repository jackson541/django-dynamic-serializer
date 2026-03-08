"""
Virtual model definitions for tests that use django-virtual-models.

VirtualAuthor, VirtualReview, and VirtualBook provide a prefetching layer
for Author, Review, and Book respectively. HAS_VIRTUAL_MODELS is True when
the library is installed.
"""
try:
    import django_virtual_models as v

    from .models import Author, Book, Review

    class VirtualAuthor(v.VirtualModel):
        """Virtual model for Author; resolved via prefetch_related (not select_related) by django-virtual-models."""

        class Meta:
            model = Author

    class VirtualReview(v.VirtualModel):
        """Virtual model for Review; prefetched via reverse FK from Book."""

        class Meta:
            model = Review

    class VirtualBook(v.VirtualModel):
        """
        Virtual model for Book with nested VirtualAuthor and VirtualReview.

        django-virtual-models uses ``prefetch_related`` for all relations,
        including the forward FK ``author``. For the reverse FK, ``review_list``
        uses ``lookup='reviews'`` to prefetch into ``to_attr='review_list'``,
        avoiding a conflict with Book's ``reviews`` RelatedManager.
        """
        author = VirtualAuthor()
        review_list = VirtualReview(lookup="reviews")

        class Meta:
            model = Book

    HAS_VIRTUAL_MODELS = True

except ImportError:
    HAS_VIRTUAL_MODELS = False
