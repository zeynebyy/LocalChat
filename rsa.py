from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
import base64

# ---------- RSA ANAHTAR ÜRETİMİ ----------
key = RSA.generate(2048)                 # 2048 bit RSA anahtarı
public_key = key.publickey().export_key()
private_key = key.export_key()

# ---------- ŞİFRELEME ----------
def rsa_encrypt(text, public_key):
    rsa_key = RSA.import_key(public_key)
    cipher = PKCS1_OAEP.new(rsa_key)
    encrypted = cipher.encrypt(text.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")

# ---------- ŞİFRE ÇÖZME ----------
def rsa_decrypt(enc_text, private_key):
    rsa_key = RSA.import_key(private_key)
    cipher = PKCS1_OAEP.new(rsa_key)
    decrypted = cipher.decrypt(base64.b64decode(enc_text))
    return decrypted.decode("utf-8")

# ---------- TEST ----------
plaintext = "Merhaba RSA şifreleme çalışıyor!"
encrypted_text = rsa_encrypt(plaintext, public_key)
decrypted_text = rsa_decrypt(encrypted_text, private_key)

print("Orijinal Metin :", plaintext)
print("Şifreli Metin  :", encrypted_text)
print("Çözülmüş Metin :", decrypted_text)
