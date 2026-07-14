from typing import Dict, Tuple, Type

from pyscript import web, when, window

from eddsa_threshold.frost.core.frost_types import SessionId
from coordinator import CoordinatorView
from participant import ParticipantView
from eddsa_threshold.frost.trusted_dealer import FrostTrustedDealer
from eddsa_threshold.eddsa.curves.base.edwards_curve import EdwardsCurve
from eddsa_threshold.eddsa.curves.ed25519.ed25519_curve import Ed25519Curve
from eddsa_threshold.eddsa.curves.ed448.ed448_curve import Ed448Curve
from eddsa_threshold.frost.core.base.frost_hashing import FrostHashing
from eddsa_threshold.frost.core.ed25519.frost_hashing import Ed25519FrostHashing
from eddsa_threshold.frost.core.ed448.frost_hashing import Ed448FrostHashing

from util import UserAbort, get_bytes_from_input, set_status

ALGORITHMS: Dict[str, Tuple[Type, Type]] = {
    "ed25519": (Ed25519Curve, Ed25519FrostHashing),
    "ed448": (Ed448Curve, Ed448FrostHashing)
}

participants: list[ParticipantView] | None = None
coordinator: CoordinatorView | None = None
trusted_dealer: FrostTrustedDealer | None = None

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

    clear_all(None)


@when("click", "#dealer-clear-all-button")
def clear_all(event):
    if event is not None and not window.confirm("Are you sure you want to clear all inputs and reset the state? This will remove all participants, coordinator, and dealer information."):
        return

    # trusted dealer tab
    clear_dealer_input()
    web.page["group-public-key"].value = ""
    web.page["dealer-status"].hidden = True
    web.page["dealer-generate-button"].disabled = False

    # coordinator tab
    clear_signing_session_input()
    # clear session info
    web.page["coordinator-sessions-container"].innerHTML = ""
    # disable session creation button until dealer info is set
    web.page["coordinator-create-signing-session-button"].disabled = True
    web.page["coordinator-status"].hidden = False
    set_status("coordinator-status",
               "Please generate shares for all participants in the dealer tab first.", "warning")

    # participant tab
    web.page["participants-container"].innerHTML = ""
    web.page["participants-status"].hidden = False
    set_status("participants-status",
               "Please generate shares for all participants in the dealer tab first.", "warning")

    # verification tab
    # web.page["verify-status"].hidden = True

    # clear state
    global participants
    global coordinator
    global trusted_dealer

    participants = None
    coordinator = None
    trusted_dealer = None


@when("click", "#dealer-generate-button")
def generate():
    global participants
    global coordinator
    global trusted_dealer

    status_element = "dealer-status"

    threshold = int(web.page["threshold"].value)
    participant_count = int(web.page["participant-count"].value)
    participant_ids = [i for i in range(1, participant_count + 1)]

    participants = []
    participant_connections_dealer = {}
    participant_connections_coordinator = {}

    try:
        for i in participant_ids:
            p_i = ParticipantView(
                i, threshold, participant_count, frost_hashing, curve)
            participants.append(p_i)
            participant_connections_dealer[i] = lambda share, vss_commitment, p=p_i: p.set_and_verify_dealer_info(
                share, vss_commitment)

        coordinator = CoordinatorView(
            threshold, participant_ids, frost_hashing, curve)
        # TODO: get existing secret
        trusted_dealer = FrostTrustedDealer.generate(
            threshold, participant_ids, participant_connections_dealer, lambda vss_commitment: coordinator.set_dealer_info(vss_commitment), curve)

        for p_i in participants:
            p_i.set_coordinator_connections(
                lambda session_id, participant_id, commitment, coordinator=coordinator: coordinator.receive_commitment(
                    session_id, participant_id, commitment),
                lambda session_id, participant_id, signature_share, coordinator=coordinator: coordinator.receive_signature_share(
                    session_id, participant_id, signature_share)
            )
            participant_connections_coordinator[p_i.ID] = lambda signing_package, p=p_i: p.receive_signing_package(signing_package)

        coordinator.set_participant_connections(participant_connections_coordinator)

        trusted_dealer.keygen()

        # TODO: choose output format
        web.page["group-public-key"].value = str(coordinator.group_public_key)

        set_status(
            status_element, "Successfully generated shares for all participants. You can now proceed to the coordinator tab.", "success")

        web.page["coordinator-create-signing-session-button"].disabled = False
        web.page["dealer-generate-button"].disabled = True
        web.page["coordinator-status"].hidden = True
        web.page["participants-status"].hidden = True
    except ValueError as e:
        set_status(status_element, f"Error generating shares: {e}", "error")
        return


@when("click", "#dealer-clear-button")
def clear_dealer_input():
    web.page["participant-count"].value = "3"
    web.page["threshold"].value = "2"
    web.page["dealer-use-existing-secret"].checked = True
    web.page["dealer-existing-secret-section"].style["display"] = "none"
    web.page["dealer-existing-secret"].value = ""


@when("click", "#coordinator-create-signing-session-button")
def create_signing_session():
    global coordinator

    status_element = "coordinator-status"

    try:
        message = get_bytes_from_input("coordinator-message", status_element)
        coordinator.create_signing_session(message)
    except UserAbort:
        # already handled
        pass


@when("click", "#coordinator-clear-button")
def clear_signing_session_input():
    web.page["coordinator-message"].value = ""


update_algorithm_info()
