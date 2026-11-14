import os
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

os.makedirs("core/keys", exist_ok=True)

priv = ed25519.Ed25519PrivateKey.generate()
pub = priv.public_key()

# 保存私钥
with open("core/keys/license_priv.pem", "wb") as f:
    f.write(priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ))

# 保存公钥
with open("core/keys/license_pub.pem", "wb") as f:
    f.write(pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ))

print("✅ 新的 Ed25519 公钥和私钥已生成！")
print("私钥路径: core/keys/license_priv.pem")
print("公钥路径: core/keys/license_pub.pem")