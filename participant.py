import re
from typing import Callable

from pyscript import web

from eddsa_threshold.frost.participant import FrostParticipant
from eddsa_threshold.frost.core.frost_types import NonceCommitment, ParticipantId, SecretShare, SecretValue, SessionId, SigningPackage, VSSCommitment
from eddsa_threshold.eddsa.curves.base.edwards_curve import EdwardsCurve
from eddsa_threshold.frost.core.base.frost_hashing import FrostHashing


class ParticipantView:
    def __init__(self, participant_id: ParticipantId, threshold: int, max_participants: int, hashing: FrostHashing, curve: EdwardsCurve):
        self.ID = participant_id
        self._PARTICIPANT = FrostParticipant(
            participant_id, threshold, max_participants, hashing, curve)
        self._signing_packages: dict[SessionId, SigningPackage] = {}

        participant_template = web.page["participant-template"].innerHTML
        participant_html = re.sub(
            r">\s+<", "><", re.sub(r"\s+", " ", participant_template)).strip()
        participant_html = participant_html.replace(
            "{participant_id}", str(self.ID))

        web.page["participants-container"].insertAdjacentHTML(
            "beforeend", participant_html)

    def set_coordinator_connections(self, coordinator_round_one: Callable[[SessionId, ParticipantId, NonceCommitment], None], coordinator_round_two: Callable[[SessionId, ParticipantId, SecretValue], None]):
        self._coordinator_round_one = coordinator_round_one
        self._coordinator_round_two = coordinator_round_two

    def set_and_verify_dealer_info(self, secret_share: SecretShare, vss_commitment: list[VSSCommitment]) -> None:
        self._PARTICIPANT.set_and_verify_dealer_info(
            secret_share, vss_commitment)

    def round_one_commit(self, session_id: SessionId) -> None:
        self._coordinator_round_one(
            session_id, self.ID, self._PARTICIPANT.round_one_commit(session_id))

    def receive_signing_package(self, signing_package: SigningPackage) -> None:
        self._signing_packages[signing_package.session_id] = signing_package

    def round_two_sign(self, session_id: SessionId) -> None:
        signing_package = self._signing_packages.get(session_id)
        if signing_package is None:
            raise ValueError(
                f"Participant {self.ID} has not received a signing package for session {session_id}")
        self._coordinator_round_two(
            session_id, self.ID, self._PARTICIPANT.round_two_sign(signing_package))
