from app.core.errors import raise_feature_not_ready


def module_placeholder(module_name: str) -> None:
    raise_feature_not_ready(module_name)
