from enum import Enum


class KookAdminStrategy(Enum):
    nobody = "nobody"
    everyone = "everyone"
    must_have_permission = "must_have_permission"
