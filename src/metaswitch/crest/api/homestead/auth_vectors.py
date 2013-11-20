class AuthVector(object):
    pass

class DigestAuthVector(AuthVector):
    def __init__(self, ha1, realm, qop):
        self.type = "digest"
        self.ha1 = ha1
        self.realm = realm or settings.SIP_DIGEST_REALM
        self.qop = qop or "auth"

    def to_json(self):
        return {"digest": {"ha1": self.ha1, "realm": self.realm, "qop": self.qop}}

class AKAAuthVector(AuthVector):
    def __init__(self, challenge, response, crypt_key, integrity_key):
        self.type = "aka"
        self.challenge, self.response, self.crypt_key, self.integrity_key = challenge, response, crypt_key, integrity_key

    def to_json(self):
        return {"aka": {"challenge": self.challenge,
                        "response": self.response,
                        "cryptkey": self.crypt_key,
                        "integritykey": self.integrity_key}}
