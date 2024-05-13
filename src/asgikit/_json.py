import importlib
import os


def _import(dotted_path: str):
    if "." not in dotted_path:
        raise ValueError(dotted_path)

    module_name, attibute_name = dotted_path.rsplit(".", maxsplit=1)
    module = importlib.import_module(module_name)
    return getattr(module, attibute_name)


if json_encoder := os.environ.get("ASGIKIT_JSON_ENCODER"):
    if "," in json_encoder:
        encoder, decoder = [
            name.strip() for name in json_encoder.split(",", maxsplit=1)
        ]
    else:
        name = json_encoder.strip()
        encoder = f"{name}.dumps"
        decoder = f"{name}.loads"
    try:
        JSON_ENCODER = _import(encoder)
        JSON_DECODER = _import(decoder)
    except ImportError as err:
        raise ValueError(f"Invalid ASGIKIT_JSON_ENCODER: {json_encoder}") from err
else:
    import json

    JSON_ENCODER = json.dumps
    JSON_DECODER = json.loads
