from django.db import connection


class VolatileTenant:
    is_dynamic = False

    @staticmethod
    def create(schema_name, domain_url):
        tenant = VolatileTenant()
        tenant.schema_name = schema_name
        tenant.domain_url = domain_url
        return tenant

    def __enter__(self):
        """
        Syntax sugar which helps in celery tasks, cron jobs, and other scripts

        Usage:
            with Tenant.objects.get(schema_name='test') as tenant:
                # run some code in tenant test
            # run some code in previous tenant (public probably)
        """
        self.previous_schema = connection.schema_name
        self.activate()

    def __exit__(self, exc_type, exc_val, exc_tb):
        connection.set_schema(self.previous_schema)

    def activate(self):
        """
        Syntax sugar that helps at django shell with fast tenant changing

        Usage:
            Tenant.objects.get(schema_name='test').activate()
        """
        connection.set_schema(self.schema_name)

    @classmethod
    def deactivate(cls):
        """
        Syntax sugar, return to public schema

        Usage:
            test_tenant.deactivate()
            # or simpler
            Tenant.deactivate()
        """
        connection.set_schema_to_public()
