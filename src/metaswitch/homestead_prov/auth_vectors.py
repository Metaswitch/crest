# Copyright (C) Metaswitch Networks 2017
# If license terms are provided to you in a COPYING file in the root directory
# of the source code repository by which you are accessing this code, then
# the license outlined in that COPYING file applies to your use.
# Otherwise no rights are granted except for those provided to you by
# Metaswitch Networks in a separate written agreement.

from metaswitch.crest import settings
from . import authtypes

class AuthVector(object):
    def to_json(self):
        raise NotImplementedError

class DigestAuthVector(AuthVector):
    def __init__(self, ha1, realm, qop):
        self.type = authtypes.SIP_DIGEST
        self.ha1 = ha1
        self.realm = realm or settings.SIP_DIGEST_REALM
        self.qop = qop or "auth"

    def to_json(self):
        return {"digest": {"ha1": self.ha1, "realm": self.realm, "qop": self.qop}}

class AKAAuthVector(AuthVector):
    def __init__(self, challenge, response, crypt_key, integrity_key):
        self.type = authtypes.AKA
        self.challenge, self.response, self.crypt_key, self.integrity_key = challenge, response, crypt_key, integrity_key

    def to_json(self):
        return {"aka": {"challenge": self.challenge,
                        "response": self.response,
                        "cryptkey": self.crypt_key,
                        "integritykey": self.integrity_key}}
