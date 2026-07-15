from dataclasses import dataclass
import re
from typing import Callable

from pyscript import web

from eddsa_threshold.frost.participant import FrostParticipant
from eddsa_threshold.frost.core.frost_types import NonceCommitment, ParticipantId, SecretShare, SecretValue, SessionId, SigningPackage, VSSCommitment
from eddsa_threshold.eddsa.curves.base.edwards_curve import EdwardsCurve
from eddsa_threshold.frost.core.base.frost_hashing import FrostHashing

from util import get_short_session_id_with_dots, set_status

@dataclass
class ParticipantSession:
    joined: bool = False
    started: bool = False
    commitment: NonceCommitment | None = None
    committed: bool = False
    signing_package: SigningPackage | None = None
    signature_share: SecretValue | None = None 
    signed: bool = False
    
class ParticipantView:
    def __init__(self, participant_id: ParticipantId, threshold: int, max_participants: int, hashing: FrostHashing, curve: EdwardsCurve):
        self.ID = participant_id
        self._PARTICIPANT = FrostParticipant(
            participant_id, threshold, max_participants, hashing, curve)
        self._available_sessions: set[SessionId] = set()
        self._participant_sessions: dict[SessionId, ParticipantSession] = {}
        self._STATUS_ELEMENT = f"participant-status-{participant_id}"

        participant_template = web.page["participant-template"].innerHTML
        participant_html = re.sub(
            r">\s+<", "><", re.sub(r"\s+", " ", participant_template)).strip()
        participant_html = participant_html.replace(
            "{participant_id}", str(self.ID))

        web.page["participants-container"].insertAdjacentHTML(
            "beforeend", participant_html)

    def set_coordinator_connections(self, coordinator_register: Callable[[SessionId, ParticipantId], None], coordinator_round_one: Callable[[SessionId, ParticipantId, NonceCommitment], None], coordinator_round_two: Callable[[SessionId, ParticipantId, SecretValue], None]):
        self._coordinator_register = coordinator_register
        self._coordinator_round_one = coordinator_round_one
        self._coordinator_round_two = coordinator_round_two

    def set_and_verify_dealer_info(self, secret_share: SecretShare, vss_commitment: list[VSSCommitment]) -> None:
        self._PARTICIPANT.set_and_verify_dealer_info(
            secret_share, vss_commitment)

    def add_available_session(self, session_id: SessionId) -> None:
        self._available_sessions.add(session_id)
        id = str(session_id)
        web.page[f"participant-available-sessions-{self.ID}"].options.add(
            value=id, html=get_short_session_id_with_dots(id))

    def remove_available_session(self, session_id: SessionId) -> None:
        self._available_sessions.remove(session_id)
        select = web.page[f"participant-available-sessions-{self.ID}"]
        select.options.remove(select.options.selected.index)

    def join_session_by_id(self, session_id: SessionId) -> None:
        if session_id not in self._available_sessions:
            raise ValueError(
                f"Participant {self.ID} cannot join session {session_id} because it is not available")
        self._coordinator_register(session_id, self.ID)
        self._participant_sessions[session_id] = ParticipantSession(joined=True)
        self.remove_available_session(session_id)

        session_template = web.page["participant-session-template"].innerHTML
        session_html = re.sub(
            r">\s+<", "><", re.sub(r"\s+", " ", session_template)).strip()
        session_html = session_html.replace("{participant_id}", str(
            self.ID)).replace("{session_id}", str(session_id))

        web.page[f"participant-sessions-container-{self.ID}"].insertAdjacentHTML(
            "beforeend", session_html)
        
    def mark_session_as_started(self, session_id: SessionId) -> None:
        if session_id not in self._participant_sessions:
            raise ValueError(
                f"Participant {self.ID} cannot mark session {session_id} as started because it has not joined it")
        self._participant_sessions[session_id].started = True
        self.update_session_info(session_id)

    def round_one_commit(self, session_id: SessionId) -> None:
        if session_id not in self._participant_sessions or not self._participant_sessions[session_id].joined:
            # should not happen, because the commit button is not there
            raise ValueError(
                f"Participant {self.ID} cannot commit to session {session_id} because it has not joined it")
        try:
            self._coordinator_round_one(
                session_id, self.ID, self._PARTICIPANT.round_one_commit(session_id))
            self._participant_sessions[session_id].committed = True
        except Exception as e:
            set_status(self._STATUS_ELEMENT, f"Error during round one commit for session {session_id}: {str(e)}", "error")

    def receive_signing_package(self, signing_package: SigningPackage) -> None:
        self._participant_sessions[signing_package.session_id].signing_package = signing_package

    def round_two_sign(self, session_id: SessionId) -> None:
        signing_package = self._participant_sessions[session_id].signing_package
        try:
            if signing_package is None:
                raise ValueError(
                    f"Participant {self.ID} has not received a signing package for session {session_id}")
            self._coordinator_round_two(
                session_id, self.ID, self._PARTICIPANT.round_two_sign(signing_package))
            self._participant_sessions[session_id].signed = True
        except Exception as e:
            set_status(self._STATUS_ELEMENT, f"Error during round two sign for session {session_id}: {str(e)}", "error")

    def update_session_info(self, session_id: SessionId) -> None:
        joined = self._participant_sessions[session_id].joined
        started = self._participant_sessions[session_id].started
        committed = self._participant_sessions[session_id].committed
        signed = self._participant_sessions[session_id].signed
        
        output = ""
        output += f"Joined: {joined}\n"
        output += f"Started: {started}\n"
        output += f"Commitment: {self._participant_sessions[session_id].commitment}\n"
        output += f"Committed: {committed}\n"
        output += f"Signing Package: {self._participant_sessions[session_id].signing_package}\n"
        output += f"Signature Share: {self._participant_sessions[session_id].signature_share}\n"
        output += f"Signed: {signed}"

        web.page[f"participant-{self.ID}-session-{session_id}"].value = output
        
        if joined and started and not committed:
            web.page[f"participant-{self.ID}-session-{session_id}-commit-button"].disabled = False
            web.page[f"participant-{self.ID}-session-{session_id}-sign-button"].disabled = True
        elif joined and started and committed and not signed:
            web.page[f"participant-{self.ID}-session-{session_id}-commit-button"].disabled = True
            web.page[f"participant-{self.ID}-session-{session_id}-sign-button"].disabled = False
        elif (joined and started and committed and signed) or (joined and not started):
            web.page[f"participant-{self.ID}-session-{session_id}-commit-button"].disabled = True
            web.page[f"participant-{self.ID}-session-{session_id}-sign-button"].disabled = True