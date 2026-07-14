from base64 import b64encode, b64decode
import ast
from pyscript import web


class UserAbort(Exception):
    pass


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

    raise ValueError(f"Unsupported format: {fmt}")


def get_bytes_from_input(input_element: str, status_element: str) -> bytes:
    return _decode_bytes(''.join(web.page[input_element].value), ''.join(web.page[f"{input_element}-format"].value), status_element)


def _decode_bytes(data: str, fmt: str, status_element: str) -> bytes:
    if fmt == "text":
        try:
            return data.encode()
        except ValueError as e:
            set_status(status_element, f"Invalid text input: {e}", "error")
            raise UserAbort(f"Invalid text input: {e}")

    if fmt == "hex":
        try:
            return bytes.fromhex(data.strip())
        except ValueError as e:
            set_status(status_element, f"Invalid hex input: {e}", "error")
            raise UserAbort(f"Invalid hex input: {e}")

    if fmt == "base64":
        try:
            return b64decode(data.strip())
        except ValueError as e:
            set_status(status_element, f"Invalid Base64 input: {e}", "error")
            raise UserAbort(f"Invalid Base64 input: {e}")

    if fmt == "python":
        try:
            obj = ast.literal_eval(data)
            if not isinstance(obj, bytes):
                raise ValueError("Expected bytes literal")
            return obj
        except (ValueError, SyntaxError) as e:
            set_status(status_element,
                       f"Invalid Python bytes literal: {e}", "error")
            raise UserAbort(f"Invalid Python bytes literal: {e}")

    set_status(status_element, f"Unsupported format: {fmt}", "error")
    raise ValueError(f"Unsupported format: {fmt}")


def get_short_session_id(session_id: str) -> str:
    return str(session_id)[:8] + str(session_id)[-8:]

def get_short_session_id_with_dots(session_id: str) -> str:
    return str(session_id)[:8] + "..." + str(session_id)[-8:]
