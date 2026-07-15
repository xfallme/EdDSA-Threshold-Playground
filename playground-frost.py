from typing import Dict, Tuple, Type

from pyscript import web, when, window
from pyodide.ffi.wrappers import add_event_listener
from js import copyToClipboard

from eddsa_threshold.frost.core.frost_types import ParticipantId, SessionId
from coordinator import CoordinatorView
from participant import ParticipantView
from eddsa_threshold.frost.trusted_dealer import FrostTrustedDealer
from eddsa_threshold.eddsa.curves.base.edwards_curve import EdwardsCurve
from eddsa_threshold.eddsa.curves.ed25519.ed25519_curve import Ed25519Curve
from eddsa_threshold.eddsa.curves.ed448.ed448_curve import Ed448Curve
from eddsa_threshold.frost.core.base.frost_hashing import FrostHashing
from eddsa_threshold.frost.core.ed25519.frost_hashing import Ed25519FrostHashing
from eddsa_threshold.frost.core.ed448.frost_hashing import Ed448FrostHashing
from eddsa_threshold.eddsa.algorithms.ed25519 import Ed25519
from eddsa_threshold.eddsa.algorithms.ed448 import Ed448

from util import UserAbort, get_bytes_from_input, get_short_session_id_with_dots, set_output, set_output_format_element_override, set_status, add_format_change_listener

ALGORITHMS: Dict[str, Tuple[Type, Type]] = {
    "ed25519": (Ed25519Curve, Ed25519FrostHashing),
    "ed448": (Ed448Curve, Ed448FrostHashing)
}

participants: Dict[ParticipantId, ParticipantView] | None = None
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
    web.page["participant-count"].value = "3"
    web.page["threshold"].value = "2"
    web.page["dealer-use-existing-secret"].checked = True
    web.page["dealer-existing-secret-section"].style["display"] = "none"
    web.page["dealer-existing-secret"].value = ""
    web.page["group-public-key-output"].value = ""
    web.page["dealer-status"].hidden = True
    web.page["dealer-generate-button"].disabled = False
    web.page["dealer-existing-secret"].disabled = False

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
    clear_verify()

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

    participants = {}
    participant_connections_dealer = {}
    participant_connections_coordinator = {i: {} for i in participant_ids}

    try:
        for i in participant_ids:
            p_i = ParticipantView(
                i, threshold, participant_count, frost_hashing, curve)
            add_event_listener(
                web.page[f"participant-join-session-button-{i}"], "click", join_session)
            participants[i] = p_i
            participant_connections_dealer[i] = lambda share, vss_commitment, p=p_i: p.set_and_verify_dealer_info(
                share, vss_commitment)

        coordinator = CoordinatorView(
            threshold, participant_ids, frost_hashing, curve)
        # get existing secret and lock input
        if not web.page["dealer-use-existing-secret"].checked:
            existing_secret = get_bytes_from_input(
                "dealer-existing-secret", status_element)
            trusted_dealer = FrostTrustedDealer.from_private_bytes(
                existing_secret, threshold, participant_ids, participant_connections_dealer, lambda vss_commitment: coordinator.set_dealer_info(vss_commitment), curve)
        else:
            trusted_dealer = FrostTrustedDealer.generate(
                threshold, participant_ids, participant_connections_dealer, lambda vss_commitment: coordinator.set_dealer_info(vss_commitment), curve)
        web.page["dealer-existing-secret"].disabled = True

        for p_i in participants.values():
            p_i.set_coordinator_connections(
                lambda session_id, participant_id, coordinator=coordinator: coordinator.register_participant_to_session(
                    session_id, participant_id),
                lambda session_id, participant_id, commitment, coordinator=coordinator: coordinator.receive_commitment(
                    session_id, participant_id, commitment),
                lambda session_id, participant_id, signature_share, coordinator=coordinator: coordinator.receive_signature_share(
                    session_id, participant_id, signature_share)
            )
            participant_connections_coordinator[p_i.ID]["start_signing_session"] = lambda session_id, p=p_i: p.mark_session_as_started(
                session_id)
            participant_connections_coordinator[p_i.ID]["distribute_signing_package"] = lambda signing_package, p=p_i: p.receive_signing_package(
                signing_package)

        coordinator.set_participant_connections(
            participant_connections_coordinator)

        group_secret = trusted_dealer._seed
        trusted_dealer.keygen()

        set_output_format_element_override(
            "group-public-key-output", "group-info-output-format", coordinator.group_public_key)
        set_output_format_element_override(
            "group-secret-output", "group-info-output-format", curve.encoding.encode_scalar(group_secret))

        set_status(
            status_element, "Successfully generated shares for all participants. You can now proceed to the coordinator tab.", "success")

        web.page["coordinator-message"].disabled = False
        web.page["coordinator-create-signing-session-button"].disabled = False
        web.page["dealer-generate-button"].disabled = True
        web.page["coordinator-status"].hidden = True
        web.page["participants-status"].hidden = True
    except Exception as e:
        # on any error, we need to roll back creation of participants and coordinator, because they might be in an inconsistent state
        clear_all(None)
        set_status(status_element, f"Error generating shares: {e}", "error")


@when("click", "#coordinator-create-signing-session-button")
def create_signing_session():
    global coordinator

    status_element = "coordinator-status"

    try:
        message = get_bytes_from_input("coordinator-message", status_element)
        id = coordinator.create_signing_session(message)

        for p in participants.values():
            p.add_available_session(id)

        add_event_listener(
            web.page[f"coordinator-session-start-signing-{id}"], "click", start_session)
        add_event_listener(
            web.page[f"coordinator-session-aggregate-signature-{id}-button"], "click", aggregate_session)
        # has to be done here, because this button doesn't exist when JS runs over all buttons
        copyToClipboard(
            web.page[f"coordinator-session-copy-signature-{id}-button"])
        add_format_change_listener(
            f"coordinator-session-signature-{id}", f"coordinator-session-signature-{id}-format", status_element)

        set_status(status_element,
                   f"Successfully created signing session {get_short_session_id_with_dots(id)}. Participants can now join the session and start signing.", "success")
    except UserAbort:
        # already handled
        pass


@when("click", "#coordinator-clear-button")
def clear_signing_session_input():
    web.page["coordinator-message"].value = ""


def start_session(event):
    # listener added by add_event_listener in create_signing_session() to avoid issues with participant IDs not being available at the time of adding the listener
    session_id = SessionId(event.target.dataset.sid)
    coordinator.start_signing_session(session_id)


def join_session(event):
    # listener added by add_event_listener in generate() to avoid issues with participant IDs not being available at the time of adding the listener
    participant_id = ParticipantId(event.target.dataset.pid)
    session_id_str = web.page[f"participant-available-sessions-{participant_id}"].value
    if session_id_str == "":
        return

    session_id = SessionId(session_id_str)
    participants[participant_id].join_session_by_id(session_id)
    coordinator.update_session_info(session_id)

    # add listeners for commit and sign buttons
    add_event_listener(
        web.page[f"participant-{participant_id}-session-{session_id}-commit-button"], "click", commit_to_session)
    add_event_listener(
        web.page[f"participant-{participant_id}-session-{session_id}-sign-button"], "click", sign_session)


def commit_to_session(event):
    # listener added by add_event_listener in join_session() to avoid issues with participant IDs not being available at the time of adding the listener
    participant_id = ParticipantId(event.target.dataset.pid)
    session_id = SessionId(event.target.dataset.sid)

    participants[participant_id].round_one_commit(session_id)
    coordinator.update_session_info(session_id)


def sign_session(event):
    # listener added by add_event_listener in join_session() to avoid issues with participant IDs not being available at the time of adding the listener
    participant_id = ParticipantId(event.target.dataset.pid)
    session_id = SessionId(event.target.dataset.sid)

    participants[participant_id].round_two_sign(session_id)
    coordinator.update_session_info(session_id)


def aggregate_session(event):
    # listener added by add_event_listener in create_signing_session() to avoid issues with participant IDs not being available at the time of adding the listener
    session_id = SessionId(event.target.dataset.sid)
    coordinator.aggregate(session_id)


@when("click", "#verify-button")
def verify():
    status_element = "verify-status"

    public_key = None

    try:
        if web.page["verify-use-existing-key"].checked:
            if coordinator is None:
                set_status(
                    "verify-status", "No group public key generated yet. Please run the trusted dealer first.", "error")
                return
            public_key = coordinator.group_public_key
        else:
            public_key = get_bytes_from_input(
                "verify-public-key", status_element)

        message = get_bytes_from_input("verify-message", status_element)
        signature = get_bytes_from_input("verify-signature", status_element)

        selected_algorithm = ''.join(web.page["algorithm"].value)
        if selected_algorithm == "ed25519":
            is_valid = Ed25519.verify(signature, message, public_key)
        elif selected_algorithm == "ed448":
            is_valid = Ed448.verify(signature, message, public_key, b'')
        else:
            set_status(status_element,
                       f"Unsupported algorithm: {selected_algorithm}", "error")
            return

        if is_valid:
            set_status("verify-status", "Signature is valid.", "success")
        else:
            set_status("verify-status", "Signature is invalid.", "error")
    except UserAbort:
        # already handled
        pass


@when("click", "#clear-verify-button")
def clear_verify():
    web.page["verify-public-key"].value = ""
    web.page["verify-message"].value = ""
    web.page["verify-signature"].value = ""
    web.page["verify-use-existing-key"].checked = True
    web.page["verify-public-key-section"].style["display"] = "none"
    web.page["verify-status"].hidden = True


update_algorithm_info()

# format change listeners for all input/output elements that are present at site creation
add_format_change_listener(["group-public-key-output", "group-secret-output"],
                           "group-info-output-format", "dealer-status")
