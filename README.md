# django-dynamic-serializer

Dynamically select which fields a Django REST Framework serializer returns.

By serializing only the fields you actually need, you reduce payload size **and** improve database performance — unrequested relations are never serialized, making it easy to pair with `only()` / `defer()` / `Prefetch` on your queryset so the database only fetches what the view requires.

## Installation

```bash
pip install django-dynamic-serializer
```

## Quick start

### 1. Add the mixin to your serializer

### 2. Add the view mixin and declare the fields you need

Only the fields listed above will appear in the response. Every other field on each serializer is automatically excluded.

### 3. Using the serializer directly (without the view mixin)

You can also pass `fields` when instantiating the serializer manually:


## Field specification format

| Entry type | Meaning |
|---|---|
| `"field_name"` | Include a top-level field |
| `{"object_name": "nested", "fields": [...]}` | Include a nested serializer and recursively select its fields |

Nesting can go as deep as your serializer hierarchy requires.

## How it improves database performance

When you only declare the fields you need:

1. **Smaller payloads** — less data serialized and sent over the wire.
2. **Fewer DB queries** — nested serializers that aren't requested are never accessed, so their related-object lookups are skipped entirely.
3. **Easy to combine with queryset optimizations** — since you know exactly which relations will be serialized, you can precisely tailor `select_related()`, `prefetch_related()`, `only()`, and `defer()` to match.

## License

[MIT](LICENSE)
