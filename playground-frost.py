from typing import Dict, Tuple, Type

from pyscript import web, when

from eddsa_threshold.frost.coordinator import FrostCoordinator
from eddsa_threshold.frost.trusted_dealer import FrostTrustedDealer
from eddsa_threshold.frost.participant import FrostParticipant
from eddsa_threshold.eddsa.curves.base.edwards_curve import EdwardsCurve
from eddsa_threshold.eddsa.curves.ed25519.ed25519_curve import Ed25519Curve
from eddsa_threshold.eddsa.curves.ed448.ed448_curve import Ed448Curve
from eddsa_threshold.frost.core.base.frost_hashing import FrostHashing
from eddsa_threshold.frost.core.ed25519.frost_hashing import Ed25519FrostHashing
from eddsa_threshold.frost.core.ed448.frost_hashing import Ed448FrostHashing

ALGORITHMS: Dict[str, Tuple[Type, Type]] = {
    "ed25519": (Ed25519Curve, Ed25519FrostHashing),
    "ed448": (Ed448Curve, Ed448FrostHashing)
}

participants = None
coordinator = None
trusted_dealer = None

curve = EdwardsCurve | None
frost_hashing = FrostHashing | None


@when("change", "#algorithm")
def update_algorithm_info():
    global curve
    global frost_hashing

    selected_algorithm = ''.join(web.page["algorithm"].value)

    curve_cls, frost_hashing_cls = ALGORITHMS[selected_algorithm]
    curve = curve_cls()
    frost_hashing = frost_hashing_cls()

    print("ready to use curve class:", curve_cls.__name__,
          "and frost hashing class:", frost_hashing_cls.__name__)

    clear_all()


@when("click", "#dealer-clear-all-button")
def clear_all():
    # trusted dealer tab
    clear_dealer()
    web.page["group-public-key"].value = ""

    # coordinator tab
    # clear session info
    web.page["coordinator-sessions-container"].innerHTML = ""

    # clear state
    global participants
    global coordinator
    global trusted_dealer

    participants = None
    coordinator = None
    trusted_dealer = None


@when("click", "#dealer-generate-button")
def create():
    global participants
    global coordinator
    global trusted_dealer

    threshold = int(web.page["threshold"].value)
    participant_count = int(web.page["participant-count"].value)
    participant_ids = [i for i in range(1, participant_count + 1)]

    participants = []
    participant_connections = {}
    for i in participant_ids:
        p_i = FrostParticipant(
            i, threshold, participant_count, frost_hashing, curve)
        participants.append(p_i)
        participant_connections[i] = lambda share, vss_commitment, p=p_i: p.set_and_verify_dealer_info(
            share, vss_commitment)

    coordinator = FrostCoordinator(
        threshold, participant_ids, frost_hashing, curve)
    trusted_dealer = FrostTrustedDealer.generate(
        threshold, participant_ids, participant_connections, lambda vss_commitment: coordinator.set_dealer_info(vss_commitment), curve)

    trusted_dealer.keygen()

    group_info = coordinator._GROUP_INFO

    web.page["group-public-key"].value = str(group_info.group_public_key)


@when("click", "#dealer-clear-button")
def clear_dealer():
    web.page["participant-count"].value = "3"
    web.page["threshold"].value = "2"
    web.page["dealer-use-existing-secret"].checked = True
    web.page["dealer-existing-secret-section"].style["display"] = "none"
    web.page["dealer-existing-secret"].value = ""


update_algorithm_info()
