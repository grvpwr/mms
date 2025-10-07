import jpype, os, glob, base64
from pathlib import Path
# from djangoproject.settings import BASE_DIR

def run_jvm():
    BASE_DIR = Path(__file__).resolve().parent.parent
    PROJECT_ROOT = os.path.join(BASE_DIR, "crypto_java")
    THIN_JAR = os.path.join(PROJECT_ROOT, "target", "npci-pkcs-1.0.jar")
    LIB_DIR = os.path.join(PROJECT_ROOT, "target", "lib")

    lib_jars = sorted(glob.glob(os.path.join(LIB_DIR, "*.jar")))
    classpath_entries = [THIN_JAR] + lib_jars
    classpath_str = os.pathsep.join(classpath_entries)

    if not jpype.isJVMStarted():
        jpype.startJVM("-Djava.class.path=" + classpath_str)
        print("JVM is now running", end=" - ")
        print(jpype.JClass("GatewayClass").test())
    else:
        print("JVM already running", end=" - ")
        print(jpype.JClass("GatewayClass").test())

def encrypt(data_to_encrypt) -> bytes:
    if not jpype.isJVMStarted():
        run_jvm()
    
    GatewayClass = jpype.JClass("GatewayClass")
    jvm_output = GatewayClass.encrypt(data_to_encrypt)
    return bytes(jvm_output)

def decrypt(data_to_decrypt) -> bytes:
    if not jpype.isJVMStarted():
        run_jvm()
    
    GatewayClass = jpype.JClass("GatewayClass")
    jvm_output = GatewayClass.decrypt(data_to_decrypt)
    return bytes(jvm_output)
