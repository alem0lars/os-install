Setup
=====

Automatic system setup.

Folder structure
----------------

The folder structure is like the suggested one by ansible official docs.

Commons directory
~~~~~~~~~~~~~~~~~

The only difference between a normal ansible repository is the "custom"
directory ``commons``, that contains code to be shared between library files.

So, when you make changes to any file inside ``commons`` directory, run:

.. code-block::

   $ invoke bundle_commons

Test roles
~~~~~~~~~~

To test a specific role, run:

.. code-block::

   $ invoke test $ROLE_NAME
