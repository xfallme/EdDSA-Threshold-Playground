from typing import Type, Tuple, Dict

from pyscript import web, when

from eddsa_threshold.eddsa.keys.keypair import Keypair
from eddsa_threshold.eddsa.algorithms.ed25519 import Ed25519
from eddsa_threshold.eddsa.algorithms.ed25519ph import Ed25519PH
from eddsa_threshold.eddsa.algorithms.ed25519ctx import Ed25519CTX
from eddsa_threshold.eddsa.keys.ed25519_keypair import Ed25519Keypair
from eddsa_threshold.eddsa.algorithms.ed448 import Ed448
from eddsa_threshold.eddsa.algorithms.ed448ph import Ed448PH
from eddsa_threshold.eddsa.keys.ed448_keypair import Ed448Keypair

from util import get_bytes_from_input, set_output, set_output_format_override, set_status

ALGORITHMS: Dict[str, Tuple[Type, Type]] = {
    "ed25519": (Ed25519, Ed25519Keypair),
    "ed25519ph": (Ed25519PH, Ed25519Keypair),
    "ed25519ctx": (Ed25519CTX, Ed25519Keypair),
    "ed448": (Ed448, Ed448Keypair),
    "ed448ph": (Ed448PH, Ed448Keypair)
}

algorithm_cls: Type[Ed25519] | Type[Ed25519PH] | Type[Ed25519CTX] | Type[Ed448] | Type[Ed448PH]
keypair_cls: Type[Ed25519Keypair] | Type[Ed448Keypair]
keypair: Keypair | None


@when("change", "#algorithm")
def update_algorithm_info():
    global algorithm_cls
    global keypair_cls

    selected_algorithm = ''.join(web.page["algorithm"].value)

    algorithm_cls, keypair_cls = ALGORITHMS[selected_algorithm]

    print("ready to use algorithm class:", algorithm_cls.__name__,
          "and keypair class:", keypair_cls.__name__)

    clear_keypair()
    clear_existing_keypair()
    clear_sign()
    clear_verify()


@when("click", "#generate-keypair-button")
def generate_keypair():
    global keypair_cls
    global keypair

    keypair = keypair_cls.generate()
    set_output_format_override(
        "private-key-output", "keygen-output-format", keypair.private_bytes)
    set_output_format_override(
        "public-key-output", "keygen-output-format", keypair.public_bytes)
    set_status("keygen-status",
               "Keypair generated successfully. It is now stored and ready to use in the other tabs.", "success")


@when("click", "#clear-keypair-button")
def clear_keypair():
    global keypair

    keypair = None
    web.page["private-key-output"].value = ""
    web.page["public-key-output"].value = ""
    web.page["keygen-status"].hidden = True


@when("click", "#existing-keypair-button")
def derive_keypair():
    global keypair_cls
    global keypair

    status_element = "keygen-status"

    private_key_input = get_bytes_from_input(
        "keygen-existing-private-key", status_element)
    try:
        keypair = keypair_cls.from_private_bytes(private_key_input)
        set_output_format_override(
            "private-key-output", "keygen-existing-output-format", keypair.private_bytes)
        set_output_format_override(
            "public-key-output", "keygen-existing-output-format", keypair.public_bytes)
        set_status(status_element,
                   "Keypair derived successfully. It is now stored and ready to use in the other tabs.", "success")
    except ValueError as e:
        set_status(status_element, f"Invalid private key: {e}", "error")


@when("click", "#clear-existing-keypair-button")
def clear_existing_keypair():
    clear_keypair()
    web.page["keygen-existing-private-key"].value = ""


@when("click", "#sign-button")
def sign_message():
    global algorithm_cls
    global keypair

    status_element = "sign-status"

    active_keypair = None

    if web.page["sign-use-existing-key"].checked:
        if keypair is None:
            set_status(
                "sign-status", "No keypair generated yet. Please generate a keypair first.", "error")
            return
        active_keypair = keypair
    else:
        private_key_input = get_bytes_from_input(
            "sign-private-key", status_element)
        try:
            active_keypair = keypair_cls.from_private_bytes(private_key_input)
        except ValueError as e:
            set_status(status_element, f"Invalid private key: {e}", "error")
            return

    message = get_bytes_from_input("sign-message", status_element)

    selected_algorithm = ''.join(web.page["algorithm"].value)
    if selected_algorithm in ["ed25519", "ed25519ph"]:
        # without context
        signature = algorithm_cls.sign(message, active_keypair)
    else:
        # with context
        context = get_bytes_from_input("sign-context", status_element)
        signature = algorithm_cls.sign(message, active_keypair, context)

    set_output("sign-signature-output", signature)
    set_status("sign-status", "Message signed successfully.", "success")


@when("click", "#clear-sign-button")
def clear_sign():
    web.page["sign-private-key"].value = ""
    web.page["sign-message"].value = ""
    web.page["sign-context"].value = ""
    web.page["sign-use-existing-key"].checked = False
    web.page["sign-private-key-section"].style["display"] = "flex"
    web.page["sign-signature-output"].value = ""
    web.page["sign-status"].hidden = True


@when("click", "#verify-button")
def verify_signature():
    global algorithm_cls
    global keypair

    status_element = "verify-status"

    public_key = None

    if web.page["verify-use-existing-key"].checked:
        if keypair is None:
            set_status(
                "verify-status", "No keypair generated yet. Please generate a keypair first.", "error")
            return
        public_key = keypair.public_bytes
    else:
        public_key = get_bytes_from_input("verify-public-key", status_element)

    message = get_bytes_from_input("verify-message", status_element)
    signature = get_bytes_from_input("verify-signature", status_element)

    selected_algorithm = ''.join(web.page["algorithm"].value)
    if selected_algorithm in ["ed25519", "ed25519ph"]:
        # without context
        is_valid = algorithm_cls.verify(signature, message, public_key)
    else:
        # with context
        context = get_bytes_from_input("verify-context", status_element)
        is_valid = algorithm_cls.verify(
            signature, message, public_key, context)

    if is_valid:
        set_status("verify-status", "Signature is valid.", "success")
    else:
        set_status("verify-status", "Signature is invalid.", "error")


@when("click", "#clear-verify-button")
def clear_verify():
    web.page["verify-public-key"].value = ""
    web.page["verify-message"].value = ""
    web.page["verify-signature"].value = ""
    web.page["verify-context"].value = ""
    web.page["verify-use-existing-key"].checked = False
    web.page["verify-public-key-section"].style["display"] = "flex"
    web.page["verify-status"].hidden = True


# Initialize algorithm and keypair classes on page load (set correct labels and placeholders)
update_algorithm_info()
# clear fields because the variables are not initialized yet
clear_keypair()
clear_existing_keypair()
clear_sign()
clear_verify()
