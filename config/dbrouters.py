# project/dbrouters.py

class WissendRouter:
    """
    Route AIData model to the wissendDB database.
    """

    def db_for_read(self, model, **hints):
        if model._meta.app_label == "modules_file_uploads" and model.__name__ == "AIData":
            return "wissendDB"
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == "modules_file_uploads" and model.__name__ == "AIData":
            return "wissendDB"
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # AIData table must be created only inside wissendDB
        if app_label == "modules_file_uploads" and model_name == "aidata":
            return db == "wissendDB"

        # All other models use default DB
        if db == "default":
            return True

        return None
