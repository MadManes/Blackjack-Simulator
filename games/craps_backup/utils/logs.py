# games/craps/utils/logs.py
import json, logging, logging.config, os, sys
try:
    import yaml
except Exception:
    yaml = None

def _first_existing(paths):
    for p in paths:
        if os.path.exists(p):
            return p
    return None

def setup_logging_from_yaml(path: str | None = None) -> None:
    if yaml is None:
        return

    # 1) si te pasan una ruta, usarla; si no, probar ubicaciones por defecto
    candidates = []
    if path:
        candidates.append(path)

    # raíz del repo (asumimos runner se ejecuta desde raíz)
    candidates += [
        os.path.join("configs", "logging", "craps.yaml"),
        os.path.join("configs", "logging_craps.yaml"),
        os.path.join("games", "craps", "configs", "logging_craps.yaml"),
    ]

    cfg_path = _first_existing(candidates)
    if not cfg_path:
        return

    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # 2) asegurar carpetas de handlers con filename
    for handler in cfg.get("handlers", {}).values():
        filename = handler.get("filename")
        if filename:
            os.makedirs(os.path.dirname(filename), exist_ok=True)

    logging.config.dictConfig(cfg)

def get_debug_logger():
    return logging.getLogger("craps.debug")

def j(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
