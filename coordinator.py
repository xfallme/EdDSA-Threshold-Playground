import re
from typing import Callable

from pyscript import web

from eddsa_threshold.frost.coordinator import FrostCoordinator
from eddsa_threshold.frost.core.frost_types import NonceCommitment, ParticipantId, SecretValue, SecretValue, SessionId, VSSCommitment
from eddsa_threshold.eddsa.curves.base.edwards_curve import EdwardsCurve
from eddsa_threshold.frost.core.base.frost_hashing import FrostHashing

from util import get_short_session_id_with_dots, set_output, set_status


def set_state_badge_class(element_id: str, state: str):
    web.page[element_id].className = f"state-badge {state}"


class CoordinatorView:
    def __init__(self, threshold: int, participant_ids: list[ParticipantId], hashing: FrostHashing, curve: EdwardsCurve):
        self._COORDINATOR = FrostCoordinator(
            threshold, participant_ids, hashing, curve)
        self._session_info_html: str | None = None
        self._STATUS_ELEMENT = "coordinator-status"

    @property
    def group_public_key(self) -> bytes:
        return self._COORDINATOR._GROUP_INFO.group_public_key

    def set_participant_connections(self, participant_connections: dict[ParticipantId, dict[str, Callable]]) -> None:
        self._participant_connections = participant_connections

    def set_dealer_info(self, vss_commitment: list[VSSCommitment]) -> None:
        self._COORDINATOR.set_dealer_info(vss_commitment)

    def create_signing_session(self, message: bytes) -> SessionId:
        id = self._COORDINATOR.create_signing_session(message)

        id_str = str(id)

        if self._session_info_html is None:
            session_template = web.page["coordinator-session-template"].innerHTML
            self._session_info_html = re.sub(
                r">\s+<", "><", re.sub(r"\s+", " ", session_template)).strip()

        html = self._session_info_html.replace(
            "{session_id}", id_str).replace("{short_id}", get_short_session_id_with_dots(id_str))

        web.page["coordinator-sessions-container"].insertAdjacentHTML(
            "beforeend", html)

        self.update_session_info(id)

        return id

    def update_session_info(self, session_id: SessionId) -> None:
        signing_session = self._COORDINATOR._signing_sessions[session_id]

        web.page[f"coordinator-session-id-{session_id}"].value = session_id
        web.page[f"coordinator-session-message-{session_id}"].value = signing_session.message
        if signing_session.participant_ids:
            web.page[f"coordinator-session-participant-ids-{session_id}"].value = str(
                signing_session.participant_ids)
        if signing_session.commitments:
            web.page[f"coordinator-session-commitments-{session_id}"].value = str(
                signing_session.commitments)
        if signing_session.signature_shares:
            web.page[f"coordinator-session-signature-shares-{session_id}"].value = str(
                signing_session.signature_shares)

        self.set_state_badges(session_id)

    def set_state_badges(self, session_id: SessionId) -> None:
        signing_session = self._COORDINATOR._signing_sessions[session_id]

        if signing_session.signing_in_progress:
            if signing_session.session_completed:
                set_state_badge_class(
                    f"coordinator-session-completed-{session_id}", "done")
                set_state_badge_class(
                    f"coordinator-session-signing-in-progress-{session_id}", "done")
            else:
                set_state_badge_class(
                    f"coordinator-session-signing-in-progress-{session_id}", "current")

            if signing_session.round_two_completed:
                set_state_badge_class(
                    f"coordinator-session-round-one-completed-{session_id}", "done")
                set_state_badge_class(
                    f"coordinator-session-round-two-completed-{session_id}", "done")
            else:
                if signing_session.round_one_completed:
                    set_state_badge_class(
                        f"coordinator-session-round-one-completed-{session_id}", "done")
                    set_state_badge_class(
                        f"coordinator-session-round-two-completed-{session_id}", "current")
                else:
                    set_state_badge_class(
                        f"coordinator-session-round-one-completed-{session_id}", "current")

    def register_participant_to_session(self, session_id: SessionId, participant_id: ParticipantId) -> None:
        self._COORDINATOR.register_participant_to_session(
            session_id, participant_id)
        self.update_session_info(session_id)

    def start_signing_session(self, session_id: SessionId) -> None:
        try:
            self._COORDINATOR.start_signing_session(session_id)
            self.set_state_badges(session_id)
            for participant_id in self._COORDINATOR._signing_sessions[session_id].participant_ids:
                self._participant_connections[participant_id]["start_signing_session"](session_id)
            
            web.page[f"coordinator-session-start-signing-{session_id}"].disabled = True
            self.update_session_info(session_id)
        except Exception as e:
            set_status(self._STATUS_ELEMENT, f"Error starting signing session {session_id}: {str(e)}", "error")

    def receive_commitment(self, session_id: SessionId, participant_id: ParticipantId, commitment: NonceCommitment) -> None:
        self._COORDINATOR.receive_commitment(
            session_id, participant_id, commitment)
        if self._COORDINATOR._signing_sessions[session_id].round_one_completed:
            self.distribute_signing_package(session_id)
        self.update_session_info(session_id)

    def distribute_signing_package(self, session_id: SessionId) -> None:
        signing_package = self._COORDINATOR.create_signing_package(session_id)
        self.set_state_badges(session_id)
        for participant_id in signing_package.participant_ids:
            self._participant_connections[participant_id]["distribute_signing_package"](signing_package)

    def receive_signature_share(self, session_id: SessionId, participant_id: ParticipantId, signature_share: SecretValue) -> None:
        self._COORDINATOR.receive_signature_share(
            session_id, participant_id, signature_share)
        if self._COORDINATOR._signing_sessions[session_id].round_two_completed:
            web.page[f"coordinator-session-aggregate-signature-{session_id}-button"].disabled = False
        self.update_session_info(session_id)

    def aggregate(self, session_id: SessionId) -> None:
        signature = self._COORDINATOR.aggregate(session_id)
        self.set_state_badges(session_id)
        set_output(
            f"coordinator-session-signature-{session_id}", signature)
        web.page[f"coordinator-session-aggregate-signature-{session_id}-button"].disabled = True
