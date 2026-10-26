"""Thông tin phát hành (không sửa)."""
import hashlib

_K = b'%u!`\xb4\x8f7\xf2Q\x0b\x8c\x08\x0c\x98\x04\xea'
_D = b'q\xb6\x80\x03\x94\xe8^\x13\xeb\xa8\xb6(B\xffq\x93\xc4\xce\xa4\x0e\x94\xcc\xf4F?l\xacJ\xed"\xb5\x84B'
_H = "7253481d9bb90e55bf7014de75e6016e6791b7e3aba1988fca88addb3bafea35"


def _dec():
    return bytes(b ^ _K[i % len(_K)] for i, b in enumerate(_D)).decode("utf-8")


def credit():
    s = _dec()
    if hashlib.sha256(s.encode("utf-8")).hexdigest() != _H:
        raise RuntimeError("Tệp chương trình đã bị thay đổi.")
    return s


def check(sig):
    """sig: mã kiểm tra lưu ở module khác; sai -> chương trình bị chỉnh sửa."""
    return credit() and sig == _H[7:23]
