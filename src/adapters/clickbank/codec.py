"""Decriptação das notificações instantâneas (INS 8.0).

O esquema, verificado na documentação em 2026-09-03 (ver research.md, R5):

    payload   = {"notification": "<base64>", "iv": "<base64>"}
    algoritmo = AES-256-CBC
    chave     = 32 primeiros caracteres do SHA-1 HEXADECIMAL da chave secreta
    saída     = JSON UTF-8, com padding PKCS#7

O detalhe que quebra a maioria das implementações está na derivação da chave:
é SHA-1, não SHA-256, e são os 32 primeiros caracteres do hexdigest tratados
como bytes ASCII — não os 32 primeiros bytes do digest binário.

Não há allowlist de IP. A autenticidade vem exclusivamente daqui: só quem tem a
chave secreta consegue produzir um payload que decripta em JSON válido.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from typing import Any

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

#: A rede limita a chave secreta a 16 caracteres alfanuméricos.
MAX_SECRET_KEY_LENGTH = 16


class InvalidNotification(Exception):
    """O payload não é autêntico, ou não é interpretável.

    Um evento assim é gravado como rejeitado e alertado. Nunca é descartado em
    silêncio, e nunca é aplicado ao estado.
    """


def derive_key(secret_key: str) -> bytes:
    """Chave AES-256 a partir da chave secreta da conta."""
    if not secret_key:
        raise ValueError("chave secreta vazia")
    if len(secret_key) > MAX_SECRET_KEY_LENGTH:
        raise ValueError(
            f"chave secreta tem {len(secret_key)} caracteres; a rede aceita "
            f"no máximo {MAX_SECRET_KEY_LENGTH}"
        )
    return hashlib.sha1(secret_key.encode("utf-8")).hexdigest()[:32].encode("utf-8")


def _unpad(data: bytes) -> bytes:
    if not data:
        raise InvalidNotification("texto decriptado vazio")
    pad = data[-1]
    if pad < 1 or pad > 16 or len(data) < pad:
        raise InvalidNotification("padding PKCS#7 inválido")
    if data[-pad:] != bytes([pad]) * pad:
        raise InvalidNotification("padding PKCS#7 inconsistente")
    return data[:-pad]


def decrypt(payload: dict[str, Any], secret_key: str) -> dict[str, Any]:
    """Devolve o corpo da notificação em claro.

    Levanta InvalidNotification para qualquer falha — chave errada, payload
    adulterado, JSON quebrado. O chamador não precisa distinguir os casos: em
    todos eles o evento é rejeitado do mesmo jeito.
    """
    try:
        ciphertext = base64.b64decode(payload["notification"], validate=True)
        iv = base64.b64decode(payload["iv"], validate=True)
    except KeyError as exc:
        raise InvalidNotification(f"payload sem o campo {exc.args[0]!r}") from None
    except (binascii.Error, ValueError) as exc:
        raise InvalidNotification(f"base64 inválido: {exc}") from None

    if len(iv) != 16:
        raise InvalidNotification(f"IV tem {len(iv)} bytes; AES-CBC exige 16")
    if not ciphertext or len(ciphertext) % 16:
        raise InvalidNotification("texto cifrado não é múltiplo do bloco AES")

    decryptor = Cipher(algorithms.AES(derive_key(secret_key)), modes.CBC(iv)).decryptor()
    plaintext = _unpad(decryptor.update(ciphertext) + decryptor.finalize())

    try:
        body = json.loads(plaintext.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        # Chave errada decripta em ruído: este é o caminho normal da falha
        # de autenticidade, não uma exceção exótica.
        raise InvalidNotification(f"conteúdo não é JSON UTF-8: {exc}") from None

    if not isinstance(body, dict):
        raise InvalidNotification("corpo da notificação não é um objeto JSON")
    return body


def encrypt(body: dict[str, Any], secret_key: str, iv: bytes) -> dict[str, str]:
    """Produz um payload no formato da rede.

    Existe para os testes de contrato: sem uma conta real, é assim que geramos
    entradas fiéis. Não é usado em produção.
    """
    if len(iv) != 16:
        raise ValueError("IV precisa ter 16 bytes")
    raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    pad = 16 - (len(raw) % 16)
    padded = raw + bytes([pad]) * pad
    encryptor = Cipher(algorithms.AES(derive_key(secret_key)), modes.CBC(iv)).encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()
    return {
        "notification": base64.b64encode(ciphertext).decode("ascii"),
        "iv": base64.b64encode(iv).decode("ascii"),
    }
