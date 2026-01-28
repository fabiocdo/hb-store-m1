def parse_bool(value):
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def parse_sfo_entries(output):
    entries = {}
    for line in output.splitlines():
        if " = " not in line or " : " not in line:
            continue
        left, value = line.split(" = ", 1)
        name = left.split(" : ", 1)[0].strip()
        entries[name] = value.strip()
    return entries


def parse_sfo_int(value):
    if isinstance(value, int):
        return value
    if not value:
        return None
    if value.startswith("0x"):
        try:
            return int(value, 16)
        except ValueError:
            return None
    try:
        return int(value)
    except ValueError:
        return None
