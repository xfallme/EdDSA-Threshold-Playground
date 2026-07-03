from base64 import b64encode, b64decode
import ast
from pyscript import web


def set_status(name: str, message: str, status: str = "info"):
    box = web.page[name]
    box.hidden = False
    box.className = f"status-box {status}"
    box.innerText = message


def set_output(output_element: str, data: bytes):
    set_output_format_override(
        output_element, f"{output_element}-format", data)


def set_output_format_override(output_element: str, format_element: str, data: bytes):
    web.page[output_element].value = _encode_bytes(
        data, ''.join(web.page[format_element].value))


def _encode_bytes(data: bytes, fmt: str) -> str:
    if fmt == "hex":
        return data.hex()

    if fmt == "base64":
        return b64encode(data).decode()

    if fmt == "python":
        return repr(data)

    raise ValueError(fmt)


def get_bytes_from_input(input_element: str) -> bytes:
    return _decode_bytes(''.join(web.page[input_element].value), ''.join(web.page[f"{input_element}-format"].value))


def _decode_bytes(data: str, fmt: str) -> bytes:
    if fmt == "text":
        return data.encode()

    if fmt == "hex":
        return bytes.fromhex(data.strip())

    if fmt == "base64":
        return b64decode(data.strip())

    if fmt == "python":
        obj = ast.literal_eval(data)
        if not isinstance(obj, bytes):
            raise ValueError("Expected bytes literal")
        return obj

    raise ValueError(fmt)
