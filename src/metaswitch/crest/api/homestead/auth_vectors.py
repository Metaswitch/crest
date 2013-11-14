class AuthVector(object):
    pass

class DigestAuthVector(AuthVector):
    def __init__(self, ha1, realm, qop):
        self.type = "digest"
        self.ha1, self.realm, self.qop = ha1, realm, qop

class AKAAuthVector(AuthVector):
    def __init__(self, challenge, response, crypt_key, integrity_key):
        self.type = "aka"
        self.challenge, self.response, self.crypt_key, self.integrity_key = challenge, response, crypt_key, integrity_key
