from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64
import os

# AES için 32 byte = 256 bit anahtar
key = os.urandom(32)

# CBC modu için 16 byte IV
iv = os.urandom(16)

def aes_encrypt(text, key, iv):
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(text.encode("utf-8"), AES.block_size))
    return base64.b64encode(encrypted).decode()

def aes_decrypt(enc_text, key, iv):
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = unpad(cipher.decrypt(base64.b64decode(enc_text)), AES.block_size)
    return decrypted.decode("utf-8")


# -------- TEST ---------
plaintext = "Merhaba AES şifreleme !"

# Şifrele
encrypted_text = aes_encrypt(plaintext, key, iv)

# Çöz
decrypted_text = aes_decrypt(encrypted_text, key, iv)

print("Orijinal Metin:", plaintext)
print("Şifreli Metin:", encrypted_text)
print("Çözülmüş Metin:", decrypted_text)
