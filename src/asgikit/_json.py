import os
import pkgutil


def _import(dotted_path: str):
    item = pkgutil.resolve_name(dotted_path)
    if not callable(item):
        raise TypeError(f"'{dotted_path}' is not callable")
    return item


if json_encoder := os.environ.get("ASGIKIT_JSON_ENCODER"):
    if "," in json_encoder:
        ENCODER, DECODER = [
            name.strip() for name in json_encoder.split(",", maxsplit=1)
        ]
    else:
        name = json_encoder.strip()
        ENCODER = f"{name}:dumps"
        DECODER = f"{name}:loads"
    try:
        JSON_ENCODER = _import(ENCODER)
        JSON_DECODER = _import(DECODER)
    except ImportError as err:
        raise ValueError(f"Invalid ASGIKIT_JSON_ENCODER: {json_encoder}") from err
else:
    import json

    JSON_ENCODER = json.dumps
    JSON_DECODER = json.loads
