class WissendRouter:

    def db_for_read(self, model, **hints):
        # Send ClassificationTempData to nuarkDB
        if model._meta.db_table == "classification_temp_data":
            return "nuarkDB"

        return None

    def db_for_write(self, model, **hints):
        if model._meta.db_table == "classification_temp_data":
            return "nuarkDB"

        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Block ALL migrations in nuarkDB
        if db == "nuarkDB":
            return False

        # Allow migrations in default DB
        return True
