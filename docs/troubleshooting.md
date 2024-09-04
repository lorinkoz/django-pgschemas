## Schema for tenant and domain models

The application(s) that contain the tenant model and the domain model should be in the public schema only. Making those models available in other schemas will cause unpredictable problems. This package will raise an error check if the tenant / domain application is found missing in `settings.TENANTS["public"]["APPS"]` or present in other tenant configuration.

!!! Tip

    You can silence this check through the code `pgschemas.W001`.

## Content types

Installing `django.contrib.contenttypes` outside of the public schema can lead to problems when using other static or dynamic schemas. The recommended approach is to have this app in `settings.TENANTS["public"]["APPS"]`. This package will raise a warning check if the content types app is found somewhere else.

!!! Tip

    You can silence this check through the code `pgschemas.W002`.

## Session leaking

Configuring users in a multi-tenant application can be challenging, because the user model(s) can be installed on any schema. Depending on the scope of your desired authentication mechanism, you should decide whether the user app will leave in the public schema or in each of the other static or dynamic schemas. If you do the latter, consdier that the same user ID could be repeated in multiple schemas. User ID is what makes authentication possible via the sessions app. In order to prevent session leaking, the recommended approach is to always put the user app and the session app together. This package will raise a warning check if the user app and the session app are found to not be together in the same schemas.

!!! Tip

    You can silence this check through the code `pgschemas.W003`.

## Moving apps between schemas

Regardless of which apps you have included in each schema, migrations will be tracked as being run on all of them. If you move an app between schemas, the tables will not be created in the destination schema, because migrations are considered to be run there already. In order to overcome this, you must remove all migrations of said app via

    manage.py migrate app zero --fake -s <schema_name>

and then run migrations again.

In order to remove the tables from the source app, you will have to actually do a zero migrate before removing the app from the said schema apps.

## Name clash between static and dynamic schemas

It is possible to define a static tenant whose name clashes with an existing dynamic tenant. This is especially true for the clone reference, which can be added as an afterthought in order to speed up dynamic tenant creation. It is also possible to create a dynamic tenant with a name already present in the static tenant configuration.

We do not provide an out-of-the-box validation mechanism for dynamic tenants upon creation, as attempt to prevent name clashes with static tenants. However, we do provide a system check that fails with a critical error message if a name clash is found. Since this check must query the database in order to fetch the schema name for all dynamic tenants, it is tagged as a database check, which makes it run only in database related operations and management commands. This means that the check will not be run via `runserver`, but will be run in commands like `migrate`, `cloneschema` and `createrefschema`. If absolutely needed,

!!! Tip

    you can silence this check through the code `pgschemas.W004`.
