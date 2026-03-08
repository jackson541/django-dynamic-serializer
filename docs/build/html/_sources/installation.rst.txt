Installation
============

Install from PyPI with pip:

.. code-block:: bash

   pip install django-dynamic-serializer

Requirements
------------

* Python >= 3.9
* Django >= 3.2
* Django REST Framework >= 3.0

No changes to ``INSTALLED_APPS`` are required — the library provides plain Python
mixins with no models, migrations, or template tags.

Optional: django-virtual-models
-------------------------------

For **automatic query optimization** driven by your serializer field selection,
install the optional ``django-virtual-models`` integration:

.. code-block:: bash

   pip install django-dynamic-serializer[virtual-models]

Or install ``django-virtual-models`` directly:

.. code-block:: bash

   pip install django-virtual-models>=0.1.4

See :doc:`virtual_models` for a full guide on using this integration.
