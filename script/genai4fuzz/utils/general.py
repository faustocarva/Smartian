import re
import json

def flatten_list(nested_list):
    result = []
    for item in nested_list:
        if isinstance(item, list):
            result.extend(flatten_list(item))
        else:
            result.append(item)
    return result

def json_from_text(text: str):
    match = re.search(r'\[[\s\S]*\]', text)
    if not match:
        return None
    try:
        return match.group(0)
    except json.JSONDecodeError:
        return None

def is_valid_json(json_string: str) -> bool:
    try:
        json.loads(json_string)
        return True
    except Exception as e:
        return False

def remove_swarm_hash(bytecode):
    if isinstance(bytecode, str):
        if bytecode.endswith("0029"):
            bytecode = re.sub(r"a165627a7a72305820\S{64}0029$", "", bytecode)
        if bytecode.endswith("0033"):
            bytecode = re.sub(r"5056fe.*?0033$", "5056", bytecode)
    return bytecode

def get_pcs_and_jumpis(bytecode):
    bytecode = bytes.fromhex(remove_swarm_hash(bytecode).replace("0x", ""))
    i = 0
    pcs = []
    jumpis = []
    while i < len(bytecode):
        opcode = bytecode[i]
        pcs.append(i)
        if opcode == 87: # JUMPI
            jumpis.append(hex(i))
        if opcode >= 96 and opcode <= 127: # PUSH
            size = opcode - 96 + 1
            i += size
        i += 1
    if len(pcs) == 0:
        pcs = [0]
    return (pcs, jumpis)

def discard_fields(data, fields_to_discard):
    if isinstance(data, dict):
        return {
            key: discard_fields(value, fields_to_discard)
            for key, value in data.items()
            if key not in fields_to_discard
        }
    elif isinstance(data, list):
        return [discard_fields(item, fields_to_discard) for item in data]
    else:
        return data