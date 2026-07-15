from base64 import b64encode, b64decode
import ast
from typing import List
from pyscript import web
from pyodide.ffi.wrappers import add_event_listener

from eddsa_threshold.frost.core.frost_types import SessionId


class UserAbort(Exception):
    pass


def set_status(name: str, message: str, status: str = "info"):
    box = web.page[name]
    box.hidden = False
    box.className = f"status-box {status}"
    box.innerText = message
    box.scrollIntoView()


def set_output(output_element: str, data: bytes):
    set_output_format_element_override(
        output_element, f"{output_element}-format", data)


def set_output_format_element_override(output_element: str, format_element: str, data: bytes):
    web.page[output_element].value = _encode_bytes(
        data, ''.join(web.page[format_element].value))
    

def add_format_change_listener(output_element: str | List[str], format_element: str, status_element: str):
    def on_format_change(event):
        current_format = ''.join(web.page[format_element].value)
        previous_format = web.page[format_element].dataset.previousFormat
        web.page[format_element].dataset.previousFormat = current_format
        
        if current_format == previous_format:
            return
        
        try:
            if isinstance(output_element, List):
                for oe in output_element:
                    data = _decode_bytes(''.join(web.page[oe].value), previous_format)
                    set_output_format_element_override(oe, format_element, data)
                    web.page[status_element].hidden = True
            else:
                data = _decode_bytes(''.join(web.page[output_element].value), previous_format)
                set_output_format_element_override(output_element, format_element, data)
                web.page[status_element].hidden = True
        except Exception as e:
            set_status(status_element, f"Error during conversion: {e}", "error")

    def on_focus(event):
        current_format = ''.join(web.page[format_element].value)
        web.page[format_element].dataset.previousFormat = current_format

    add_event_listener(web.page[format_element], "change", on_format_change)
    add_event_listener(web.page[format_element], "focus", on_focus)


def _encode_bytes(data: bytes, fmt: str) -> str:
    if fmt == "text":
        return data.decode()
    
    if fmt == "hex":
        return data.hex()

    if fmt == "base64":
        return b64encode(data).decode()

    if fmt == "python":
        return repr(data)

    raise ValueError(f"Unsupported format: {fmt}")


def get_bytes_from_input(input_element: str, status_element: str) -> bytes:
    try: 
        return _decode_bytes(''.join(web.page[input_element].value), ''.join(web.page[f"{input_element}-format"].value))
    except UserAbort as e:
        set_status(status_element, str(e), "error")
        raise e


def _decode_bytes(data: str, fmt: str) -> bytes:
    if fmt == "text":
        try:
            return data.encode()
        except ValueError as e:
            raise UserAbort(f"Invalid text input: {e}")

    if fmt == "hex":
        try:
            return bytes.fromhex(data.strip())
        except ValueError as e:
            raise UserAbort(f"Invalid hex input: {e}")

    if fmt == "base64":
        try:
            return b64decode(data.strip())
        except ValueError as e:
            raise UserAbort(f"Invalid Base64 input: {e}")

    if fmt == "python":
        try:
            obj = ast.literal_eval(data)
            if not isinstance(obj, bytes):
                raise ValueError("Expected bytes literal")
            return obj
        except (ValueError, SyntaxError) as e:
            raise UserAbort(f"Invalid Python bytes literal: {e}")

    raise UserAbort(f"Unsupported format: {fmt}")

def get_short_session_id_with_dots(session_id: str | SessionId) -> str:
    return str(session_id)[:8] + "..." + str(session_id)[-8:]
