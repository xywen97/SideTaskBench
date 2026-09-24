"""A closed work unit carries its entire problem, independent of any workspace."""


def is_closed(task):
    return isinstance(task.get("packet"), dict) and task["packet"].get("version") == 1


def validate_packet(task):
    if "packet" not in task:
        return
    packet = task["packet"]
    fields = {"version", "operation", "runtime", "dependencies", "input", "output", "examples"}
    if not isinstance(packet, dict) or set(packet) != fields or type(packet["version"]) is not int or packet["version"] != 1:
        raise ValueError("Unsupported closed work packet")
    if task.get("material_paths") != [] or packet["dependencies"] != []:
        raise ValueError("Closed tasks cannot depend on external files or other contributions")
    if packet["runtime"] not in {"python3-stdlib", "json"}:
        raise ValueError("Closed tasks require a portable declared runtime")
    if not isinstance(packet["operation"], str) or not packet["operation"].strip():
        raise ValueError("Closed tasks need one named operation")
    if not isinstance(packet["input"], dict) or not packet["input"]:
        raise ValueError("Closed task inputs must be included in the packet")
    if not isinstance(packet["output"], dict) or not packet["output"]:
        raise ValueError("Closed tasks need an explicit output contract")
    if not isinstance(packet["examples"], list):
        raise ValueError("Packet examples must be a list")
