import re
import json
from decimal import Decimal

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
        return fix_json_with_expressions(match.group(0))
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
    
def convert_to_wei(value) -> int:
    units = {
        "wei": Decimal("1"),
        "kwei": Decimal("1e3"),
        "babbage": Decimal("1e3"),
        "femtoether": Decimal("1e3"),
        "mwei": Decimal("1e6"),
        "lovelace": Decimal("1e6"),
        "picoether": Decimal("1e6"),
        "gwei": Decimal("1e9"),
        "shannon": Decimal("1e9"),
        "nanoether": Decimal("1e9"),
        "nano": Decimal("1e9"),
        "szabo": Decimal("1e12"),
        "microether": Decimal("1e12"),
        "micro": Decimal("1e12"),
        "finney": Decimal("1e15"),
        "milliether": Decimal("1e15"),
        "milli": Decimal("1e15"),
        "ether": Decimal("1e18"),
        "eth": Decimal("1e18"),
    }

    if isinstance(value, (int, float)):
        # Integers are assumed to be in wei
        return int(value)

    value = value.strip().lower()

    parts = value.split()

    if len(parts) == 1:
        try:
            # Try interpreting as an integer — assume wei
            return int(parts[0])
        except ValueError:
            # Try interpreting as a float — assume ETH
            number = Decimal(parts[0])
            return int(number * Decimal("1e18"))
    elif len(parts) == 2:
        number = Decimal(parts[0])
        unit = parts[1]
        if unit not in units:
            raise ValueError(f"Unknown unit: {unit}")
        multiplier = units[unit]
        return int(number * multiplier)
    else:
        raise ValueError("Invalid input format")
        
def fix_json_with_expressions(json_str):
    # Find array content with simple expressions like 2**255 or 2**8-3
    pattern = r'(\[)([^"\[\]]*?\d+\s*\*\*\s*\d+[^"\[\]]*?)(\])'
    
    # Check if pattern exists in the string
    if not re.search(pattern, json_str) and "uint256_max" not in json_str:
        return json_str  # Return original if no expressions or uint256_max found
    
    # Replace with quoted expressions
    def replacer(match):
        open_bracket = match.group(1)
        content = match.group(2)
        close_bracket = match.group(3)
        
        # Quote any expression containing **
        new_content = re.sub(r'(\d+\s*\*\*\s*\d+[^,]*)', r'"\1"', content)
        return open_bracket + new_content + close_bracket
    
    # Fix the JSON string for ** expressions
    fixed_json = re.sub(pattern, replacer, json_str)
    
    # Also replace uint256_max with "2**256 - 1"
    fixed_json = fixed_json.replace("uint256_max", '"2**256 - 1"')
    
    # Verify it's valid
    try:
        json.loads(fixed_json)
        return fixed_json
    except:
        return json_str  # Return original if something went wrong
            
