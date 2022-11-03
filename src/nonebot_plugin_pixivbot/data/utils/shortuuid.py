from shortuuid import ShortUUID

shortuuid = ShortUUID(alphabet="23456789abcdefghijkmnopqrstuvwxyz")


def gen_code():
    return shortuuid.random(length=5)
