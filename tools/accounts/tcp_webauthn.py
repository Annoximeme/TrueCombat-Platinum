"""Passkeys (WebAuthn) for TrueCombat accounts: the server side, Python standard library only.

What a passkey gives a player: a second way into their account (Windows Hello, Face ID, a phone or a security key),
so losing the Discord account does not mean losing the rank. Discord stays the way to make an account.

Only what we need: attestation "none" (we do not care which make of authenticator it is), ES256 (P-256) and EdDSA
(Ed25519) keys, discoverable credentials. Everything checked follows the WebAuthn Level 2 verification steps:
type, challenge, origin, RP id hash, user presence, signature and the signature counter.
"""
import base64
import hashlib
import json

# ----------------------------------------------------------------------------- base64url


def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def unb64u(text: str) -> bytes:
    text = str(text or "")
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


# ----------------------------------------------------------------------------- CBOR (decode only, what WebAuthn uses)

class CborError(ValueError):
    pass


def cbor_decode(data: bytes, pos: int = 0, depth: int = 0):
    """Returns (value, next position). Integers, byte and text strings, arrays, maps, true/false/null."""
    if depth > 16:
        raise CborError("too deep")
    if pos >= len(data):
        raise CborError("truncated")
    first = data[pos]
    major, info = first >> 5, first & 31
    pos += 1
    if info < 24:
        arg = info
    elif info in (24, 25, 26, 27):
        n = 1 << (info - 24)
        if pos + n > len(data):
            raise CborError("truncated")
        arg = int.from_bytes(data[pos:pos + n], "big")
        pos += n
    else:
        raise CborError("indefinite lengths are not used by WebAuthn")
    if major == 0:
        return arg, pos
    if major == 1:
        return -1 - arg, pos
    if major in (2, 3):
        if pos + arg > len(data):
            raise CborError("truncated")
        raw = data[pos:pos + arg]
        return (raw if major == 2 else raw.decode("utf-8")), pos + arg
    if major == 4:
        out = []
        for _ in range(arg):
            v, pos = cbor_decode(data, pos, depth + 1)
            out.append(v)
        return out, pos
    if major == 5:
        out = {}
        for _ in range(arg):
            k, pos = cbor_decode(data, pos, depth + 1)
            v, pos = cbor_decode(data, pos, depth + 1)
            if isinstance(k, (list, dict)):
                raise CborError("bad map key")
            out[k] = v
        return out, pos
    if major == 7:
        if info == 20:
            return False, pos
        if info == 21:
            return True, pos
        if info == 22:
            return None, pos
    raise CborError("unsupported CBOR item")


# ----------------------------------------------------------------------------- P-256 ECDSA verify (FIPS 186-4)

_P = 0xffffffff00000001000000000000000000000000ffffffffffffffffffffffff
_A = _P - 3
_B = 0x5ac635d8aa3a93e7b3ebbd55769886bc651d06b0cc53b0f63bce3c3e27d2604b
_N = 0xffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632551
_G = (0x6b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296,
      0x4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5)


def _on_curve(pt) -> bool:
    x, y = pt
    return 0 <= x < _P and 0 <= y < _P and (y * y - (x * x * x + _A * x + _B)) % _P == 0


def _jadd(p, q):
    """Jacobian point addition (None = the point at infinity)."""
    if p is None:
        return q
    if q is None:
        return p
    x1, y1, z1 = p
    x2, y2, z2 = q
    z1z1, z2z2 = z1 * z1 % _P, z2 * z2 % _P
    u1, u2 = x1 * z2z2 % _P, x2 * z1z1 % _P
    s1, s2 = y1 * z2 * z2z2 % _P, y2 * z1 * z1z1 % _P
    if u1 == u2:
        return _jdouble(p) if s1 == s2 else None
    h, r = (u2 - u1) % _P, (s2 - s1) % _P
    hh = h * h % _P
    hhh = h * hh % _P
    v = u1 * hh % _P
    x3 = (r * r - hhh - 2 * v) % _P
    y3 = (r * (v - x3) - s1 * hhh) % _P
    return (x3, y3, h * z1 * z2 % _P)


def _jdouble(p):
    if p is None:
        return None
    x, y, z = p
    if y == 0:
        return None
    yy = y * y % _P
    s = 4 * x * yy % _P
    zz = z * z % _P
    m = 3 * (x - zz) * (x + zz) % _P          # a = -3
    x3 = (m * m - 2 * s) % _P
    y3 = (m * (s - x3) - 8 * yy * yy) % _P
    return (x3, y3, 2 * y * z % _P)


def _jmul(k, p):
    out = None
    q = (p[0], p[1], 1)
    while k:
        if k & 1:
            out = _jadd(out, q)
        q = _jdouble(q)
        k >>= 1
    return out


def _affine_x(p):
    x, _, z = p
    zi = pow(z, _P - 2, _P)
    return x * zi * zi % _P


def _der_sig(sig: bytes):
    """ECDSA-Sig-Value ::= SEQUENCE { r INTEGER, s INTEGER } (strict DER)."""
    if len(sig) < 8 or sig[0] != 0x30 or sig[1] != len(sig) - 2:
        raise ValueError("bad signature")
    pos, out = 2, []
    for _ in range(2):
        if sig[pos] != 0x02:
            raise ValueError("bad signature")
        n = sig[pos + 1]
        raw = sig[pos + 2:pos + 2 + n]
        if n == 0 or len(raw) != n or (raw[0] & 0x80) or (n > 1 and raw[0] == 0 and not raw[1] & 0x80):
            raise ValueError("bad signature")
        out.append(int.from_bytes(raw, "big"))
        pos += 2 + n
    if pos != len(sig):
        raise ValueError("bad signature")
    return out


def p256_verify(x: int, y: int, msg: bytes, der: bytes) -> bool:
    if not _on_curve((x, y)):
        return False
    try:
        r, s = _der_sig(der)
    except (ValueError, IndexError):
        return False
    if not (0 < r < _N and 0 < s < _N):
        return False
    e = int.from_bytes(hashlib.sha256(msg).digest(), "big")
    w = pow(s, _N - 2, _N)
    pt = _jadd(_jmul(e * w % _N, _G), _jmul(r * w % _N, (x, y)))
    return pt is not None and _affine_x(pt) % _N == r


# ----------------------------------------------------------------------------- COSE keys

ALG_ES256, ALG_EDDSA = -7, -8


def cose_to_stored(cose: dict) -> dict:
    """The parts of a COSE public key we keep (JSON-safe)."""
    kty, alg = cose.get(1), cose.get(3)
    if kty == 2 and alg == ALG_ES256 and cose.get(-1) == 1:
        x, y = cose.get(-2), cose.get(-3)
        if isinstance(x, bytes) and isinstance(y, bytes) and len(x) == 32 and len(y) == 32 \
                and _on_curve((int.from_bytes(x, "big"), int.from_bytes(y, "big"))):
            return {"alg": ALG_ES256, "x": x.hex(), "y": y.hex()}
    if kty == 1 and alg == ALG_EDDSA and cose.get(-1) == 6:
        x = cose.get(-2)
        if isinstance(x, bytes) and len(x) == 32:
            return {"alg": ALG_EDDSA, "x": x.hex()}
    raise ValueError("Use a passkey that supports ES256 or Ed25519.")


def verify_with(stored: dict, msg: bytes, sig: bytes, ed25519_verify) -> bool:
    if stored.get("alg") == ALG_ES256:
        return p256_verify(int(stored["x"], 16), int(stored["y"], 16), msg, sig)
    if stored.get("alg") == ALG_EDDSA:
        return ed25519_verify(bytes.fromhex(stored["x"]), msg, sig)
    return False


# ----------------------------------------------------------------------------- the two ceremonies

def parse_auth_data(raw: bytes, with_credential: bool) -> dict:
    if len(raw) < 37:
        raise ValueError("bad authenticator data")
    out = {"rpIdHash": raw[:32], "flags": raw[32], "signCount": int.from_bytes(raw[33:37], "big")}
    if with_credential:
        if not raw[32] & 0x40 or len(raw) < 55:
            raise ValueError("no credential in the authenticator data")
        n = int.from_bytes(raw[53:55], "big")
        if n < 16 or n > 1023 or len(raw) < 55 + n:
            raise ValueError("bad credential id")
        out["credentialId"] = raw[55:55 + n]
        cose, _ = cbor_decode(raw, 55 + n)
        if not isinstance(cose, dict):
            raise ValueError("bad public key")
        out["key"] = cose_to_stored(cose)
    return out


def check_client_data(raw: bytes, kind: str, challenge: str, origin: str) -> None:
    try:
        cd = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        raise ValueError("bad client data") from e
    if not isinstance(cd, dict) or cd.get("type") != kind:
        raise ValueError("wrong ceremony")
    if cd.get("challenge") != challenge:
        raise ValueError("this request has expired, try again")
    if cd.get("origin") != origin:
        raise ValueError("wrong site")
    if cd.get("crossOrigin") is True:
        raise ValueError("wrong site")


def verify_registration(client_data: bytes, attestation: bytes, challenge: str, origin: str, rp_id: str) -> dict:
    """Returns {credentialId, key, signCount} or raises ValueError with a reason a player can read."""
    check_client_data(client_data, "webauthn.create", challenge, origin)
    att, _ = cbor_decode(attestation)
    if not isinstance(att, dict) or not isinstance(att.get("authData"), bytes):
        raise ValueError("bad attestation")
    ad = parse_auth_data(att["authData"], True)
    if ad["rpIdHash"] != hashlib.sha256(rp_id.encode()).digest():
        raise ValueError("wrong site")
    if not ad["flags"] & 0x01:
        raise ValueError("the passkey did not confirm you were there")
    if not ad["flags"] & 0x04:
        raise ValueError("the passkey did not check it was you (PIN, fingerprint or face)")
    return {"credentialId": ad["credentialId"], "key": ad["key"], "signCount": ad["signCount"]}


def verify_assertion(stored: dict, client_data: bytes, auth_data: bytes, signature: bytes, challenge: str,
                     origin: str, rp_id: str, old_count: int, ed25519_verify) -> int:
    """Returns the new signature counter, or raises ValueError."""
    check_client_data(client_data, "webauthn.get", challenge, origin)
    ad = parse_auth_data(auth_data, False)
    if ad["rpIdHash"] != hashlib.sha256(rp_id.encode()).digest():
        raise ValueError("wrong site")
    if not ad["flags"] & 0x01:
        raise ValueError("the passkey did not confirm you were there")
    if not ad["flags"] & 0x04:
        # a passkey signs you in on its own, so it must check it is you, not only that someone touched it
        raise ValueError("the passkey did not check it was you (PIN, fingerprint or face)")
    if not verify_with(stored, auth_data + hashlib.sha256(client_data).digest(), signature, ed25519_verify):
        raise ValueError("the passkey's signature does not match")
    count = ad["signCount"]
    if (count or old_count) and count <= old_count:
        raise ValueError("this passkey may have been copied; remove it and add it again")
    return count
