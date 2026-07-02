from typing import Type, Tuple, Dict

from pyscript import web, when

from eddsa_threshold.eddsa.keys.keypair import Keypair
from eddsa_threshold.eddsa.algorithms.ed25519 import Ed25519
from eddsa_threshold.eddsa.keys.ed25519_keypair import Ed25519Keypair
from eddsa_threshold.eddsa.algorithms.ed448 import Ed448
from eddsa_threshold.eddsa.keys.ed448_keypair import Ed448Keypair

from util import get_bytes_from_input, set_output, set_output_format_override, update_labels

ALGORITHMS: Dict[str, Tuple[Type, Type]] = {
    "ed25519": (Ed25519, Ed25519Keypair),
    "ed448": (Ed448, Ed448Keypair),
}

algorithm_cls: Type[Ed25519] | Type[Ed448]
keypair_cls: Type[Ed25519Keypair] | Type[Ed448Keypair]
keypair: Keypair | None


@when("change", "#algorithm")
def update_algorithm_info():
    global algorithm_cls
    global keypair_cls

    selected_algorithm = ''.join(web.page["algorithm"].value)

    algorithm_cls, keypair_cls = ALGORITHMS[selected_algorithm]

    update_labels(selected_algorithm)

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

# Initialize algorithm and keypair classes on page load (set correct labels and placeholders)
update_algorithm_info()
# clear fields because the variables are not initialized yet
clear_keypair()
