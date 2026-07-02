from pyscript import web, when

from eddsa_threshold.eddsa.algorithms.ed25519 import Ed25519
from eddsa_threshold.eddsa.keys.ed25519_keypair import Ed25519Keypair

# Keep state between button presses
keypair = None
signature = None


def output(text: str):
    web.page["output"].innerText = text


def get_input_message() -> bytes:
    return ''.join(web.page["message"].value).encode()


@when("click", "#generate-button")
def generate_keypair(event):
    global keypair

    output("Generating keypair...")

    keypair = Ed25519Keypair.generate()

    output(
        f"""Keypair generated!

        Public Key:

        {keypair.public_bytes.hex()}
        """
    )


@when("click", "#sign-button")
def sign(event):
    global signature

    if keypair is None:
        output("Generate a keypair first.")
        return

    message = get_input_message()
    signature = Ed25519.sign(message, keypair)

    output(
        f"""Message:

        {message.decode()}

        Signature:

        {signature.hex()}
        """
    )


@when("click", "#verify-button")
def verify(event):
    if keypair is None or signature is None:
        output("Nothing to verify.")
        return

    message = get_input_message()
    valid = Ed25519.verify(signature, message, keypair.public_bytes)

    output(
        f"""Verification result:

        {'✅ VALID' if valid else '❌ INVALID'}
        """
    )
