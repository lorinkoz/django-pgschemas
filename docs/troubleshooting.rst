Troubleshooting
===============

Content types
-------------

Installing ``django.contrib.contenttypes`` outside of the public schema can lead
to problems when using other static or dynamic schemas. The recommended approach
is to have this app in ``settings.TENANTS["public"]["APPS"]``. This package
will raise a warning check if the content types app is found somewhere else.
You can silence this check, whose code is ``pgschemas.W001``.

Session leaking
---------------

Configuring users in a multi-tenant application can be challenging, because
the user model(s) can be installed on any schema. Depending on the scope of your
desired authentication mechanism, you should decide whether the user app will
leave in the public schema or in each of the other static or dynamic schemas.
If you do the latter, consdier that the same user ID could be repeated in
multiple schemas. User ID is what makes authentication possible via the sessions
app. In order to prevent session leaking, the recommended approach is to always
put the user app and the session app together. This package will raise a warning
check if the user app and the session app are found to not be together in the
same schemas. You can silence this check, whose code is ``pgschemas.W002``.

Moving apps between schemas
---------------------------

Regardless of which apps you have included in each schema, migrations will be
tracked as being run on all of them. If you move an app between schemas, the
tables will not be created in the destination schema, because migrations are
considered to be run there already. In order to overcome this, you must remove
all migrations of said app via ``manage.py migrate app zero --fake -s schema``
and then run migrations again.

In order to remove the tables from the source app, you will have to actually
do a zero migrate before removing the app from the said schema apps.