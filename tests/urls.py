"""URL configuration for test views and integration endpoints."""
from django.urls import path

from . import views
from .virtual_models import HAS_VIRTUAL_MODELS

urlpatterns = [
    # Original views
    path("books/", views.BookListView.as_view(), name="book-list"),
    path("books/<int:pk>/", views.BookDetailView.as_view(), name="book-detail"),
    path("books/create/", views.BookCreateView.as_view(), name="book-create"),
    path("books/flat/", views.BookFlatListView.as_view(), name="book-flat-list"),
    path("books/missing/", views.MissingFieldsView.as_view(), name="book-missing"),

    # Integration — optimized (select_related + prefetch_related)
    path("integration/library/optimized/", views.LibraryOptimizedListView.as_view(), name="library-optimized"),
    path("integration/library/optimized-partial/", views.LibraryOptimizedPartialListView.as_view(), name="library-optimized-partial"),

    # Integration — unoptimized (N+1)
    path("integration/library/unoptimized/", views.LibraryUnoptimizedListView.as_view(), name="library-unoptimized"),
    path("integration/library/unoptimized-flat/", views.LibraryUnoptimizedFlatListView.as_view(), name="library-unoptimized-flat"),

    # Integration — __all__ serializers
    path("integration/library/all-fields/", views.LibraryAllFieldsListView.as_view(), name="library-all-fields"),
]

# Integration — django-virtual-models
if HAS_VIRTUAL_MODELS:
    urlpatterns += [
        path("integration/books/virtual/", views.BookVirtualModelListView.as_view(), name="book-virtual"),
        path("integration/books/virtual-flat/", views.BookVirtualModelFlatListView.as_view(), name="book-virtual-flat"),
        path("integration/books/virtual-author/", views.BookVirtualModelAuthorOnlyListView.as_view(), name="book-virtual-author"),
        path("integration/books/virtual/<int:pk>/", views.BookVirtualModelDetailView.as_view(), name="book-virtual-detail"),
    ]
