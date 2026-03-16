from . import registry


def factory():
    return "success"


registry.register("test-factory", factory, aliases=["test-alias"])
