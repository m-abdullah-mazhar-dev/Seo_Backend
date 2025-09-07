import threading

_thread_locals = threading.local()

def set_current_service(service_type):
    _thread_locals.service_type = service_type

def get_current_service():
    return getattr(_thread_locals, "service_type", "seo")  # default = seo


class MultiDBRouter:
    def db_for_read(self, model, **hints):
        service = get_current_service()
        if service == "trucking":
            return "trucking"
        return "default"

    def db_for_write(self, model, **hints):
        service = get_current_service()
        if service == "trucking":
            return "trucking"
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db in ["default", "trucking"]:
            return True
        return None
