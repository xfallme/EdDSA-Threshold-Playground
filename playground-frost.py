import re
from typing import Dict, Tuple, Type

from pyscript import web, when

from eddsa_threshold.frost.core.frost_types import SessionId
from eddsa_threshold.frost.coordinator import FrostCoordinator
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
coordinator: FrostCoordinator | None = None
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

    clear_all()


@when("click", "#dealer-clear-all-button")
def clear_all():
    # trusted dealer tab
    clear_dealer_input()
    web.page["group-public-key"].value = ""
    web.page["dealer-status"].hidden = True

    # coordinator tab
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
    participant_connections = {}

    try:
        for i in participant_ids:
            p_i = ParticipantView(
                i, threshold, participant_count, frost_hashing, curve)
            participants.append(p_i)
            participant_connections[i] = lambda share, vss_commitment, p=p_i: p.set_and_verify_dealer_info(
                share, vss_commitment)

        coordinator = FrostCoordinator(
            threshold, participant_ids, frost_hashing, curve)
        # TODO: get existing secret
        trusted_dealer = FrostTrustedDealer.generate(
            threshold, participant_ids, participant_connections, lambda vss_commitment: coordinator.set_dealer_info(vss_commitment), curve)

        for p_i in participants:
            p_i.set_coordinator_connections(
                lambda session_id, participant_id, commitment, coordinator=coordinator: coordinator.receive_commitment(
                    session_id, participant_id, commitment),
                lambda session_id, participant_id, signature_share, coordinator=coordinator: coordinator.receive_signature_share(
                    session_id, participant_id, signature_share)
            )

        trusted_dealer.keygen()

        group_info = coordinator._GROUP_INFO

        # TODO: choose output format
        web.page["group-public-key"].value = str(group_info.group_public_key)

        set_status(
            status_element, "Successfully generated shares for all participants. You can now proceed to the coordinator tab.", "success")

        web.page["coordinator-create-signing-session-button"].disabled = False
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
        id = coordinator.create_signing_session(message)
        id_str = str(id)
        short_id = get_short_session_id(id_str)

        session_template = web.page["coordinator-session-template"].innerHTML
        session_info_html = re.sub(
            r">\s+<", "><", re.sub(r"\s+", " ", session_template)).strip()
        session_info_html = session_info_html.replace(
            "{session_id}", id_str[:8] + "..." + id_str[-8:])
        session_info_html = session_info_html.replace("{short_id}", short_id)

        web.page["coordinator-sessions-container"].innerHTML += session_info_html

        update_session_info(id)
    except UserAbort:
        # already handled
        pass


# Session Management Functions

def get_short_session_id(session_id: str) -> str:
    return str(session_id)[:8] + str(session_id)[-8:]


def update_session_info(session_id: SessionId):
    global coordinator

    short_id = get_short_session_id(str(session_id))

    signing_session = coordinator._signing_sessions[session_id]

    web.page["coordinator-session-id-" + short_id].value = session_id
    web.page["coordinator-session-message-" +
             short_id].value = signing_session.message
    if signing_session.participant_ids:
        web.page["coordinator-session-participants-" +
                 short_id].value = str(signing_session.participant_ids)
    if signing_session.commitments:
        web.page["coordinator-session-commitments-" +
                 short_id].value = str(signing_session.commitments)
    if signing_session.signature_shares:
        web.page["coordinator-session-signature-shares-" +
                 short_id].value = str(signing_session.signature_shares)

    set_state_badges(session_id)


def set_state_badge_class(element_id: str, state: str):
    web.page[element_id].className = f"state-badge {state}"


def set_state_badges(session_id: SessionId):
    global coordinator

    short_id = get_short_session_id(str(session_id))
    signing_session = coordinator._signing_sessions[session_id]

    if signing_session.signing_in_progress:
        if signing_session.session_completed:
            set_state_badge_class(
                "coordinator-session-completed-" + short_id, "done")
            set_state_badge_class(
                "coordinator-session-signing-in-progress-" + short_id, "done")
        else:
            set_state_badge_class(
                "coordinator-session-signing-in-progress-" + short_id, "current")

        if signing_session.round_two_completed:
            set_state_badge_class(
                "coordinator-session-round-one-completed-" + short_id, "done")
            set_state_badge_class(
                "coordinator-session-round-two-completed-" + short_id, "done")
        else:
            if signing_session.round_one_completed:
                set_state_badge_class(
                    "coordinator-session-round-one-completed-" + short_id, "done")
                set_state_badge_class(
                    "coordinator-session-round-two-completed-" + short_id, "current")
            else:
                set_state_badge_class(
                    "coordinator-session-round-one-completed-" + short_id, "current")


update_algorithm_info()
