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

from util import get_bytes_from_input, set_output, set_output_format_override

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


@when("click", "#generate-keypair-button")
def generate_keypair():
    global keypair_cls
    global keypair

    keypair = keypair_cls.generate()
    set_output_format_override(
        "private-key-output", "keygen-output-format", keypair.private_bytes)
    set_output_format_override(
        "public-key-output", "keygen-output-format", keypair.public_bytes)


@when("click", "#clear-keypair-button")
def clear_keypair():
    global keypair

    keypair = None
    web.page["private-key-output"].value = ""
    web.page["public-key-output"].value = ""
    

@when("click", "#sign-button")    
def sign_message():
    global algorithm_cls
    global keypair

    if keypair is None:
        raise ValueError("No keypair available for signing.")

    message = get_bytes_from_input("sign-message")
    signature = algorithm_cls.sign(message, keypair)
    set_output_format_override("sign-signature-output", "sign-signature-format", signature)


@when("click", "#clear-sign-button")
def clear_sign():
    web.page["sign-use-existing-key"].checked = False
    web.page["sign-signature-output"].value = ""


# Initialize algorithm and keypair classes on page load (set correct labels and placeholders)
update_algorithm_info()
# clear fields because the variables are not initialized yet
clear_keypair()
clear_sign()
