import subprocess, shutil, base64, os, glob
from pathlib import Path

def find_java():
    java = shutil.which("java")
    if not java:
        raise RuntimeError("java not found on PATH. Set JAVA_HOME or add java to PATH.")
    return java

def call_java_for_crypto(mode_argument: str, input_bytes: bytes) -> bytes:

    timeout = 10

    # resolve these paths to dynamic at runtime.
    main_jar_path = r"/Users/gauravpawar/Dev/pkcs/PKCS Java/target/npci-pkcs.jar"
    dependencies = r"/Users/gauravpawar/Dev/pkcs/PKCS Java/target/bin"

    jar_paths = glob.glob(os.path.join(dependencies, "*.jar"))
    jar_paths = [main_jar_path] + jar_paths
    cp_arg_string = os.pathsep.join(jar_paths)

    java = find_java()
    cmd = [java, "-cp", cp_arg_string, "GatewayClass", mode_argument]

    try:
        completed = subprocess.run(
            cmd,
            input=input_bytes,               # bytes -> passed to stdin
            stdout=subprocess.PIPE,          # capture raw stdout bytes
            stderr=subprocess.PIPE,          # capture stderr for debugging
            timeout=timeout
        )
    except subprocess.TimeoutExpired as e:
        # process killed by timeout; e.stdout/e.stderr may contain partial data
        raise RuntimeError(f"java timed out after {timeout}s") from e

    if completed.returncode != 0:
        # show stderr (decoded safely) to help debugging
        stderr_text = completed.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"java exited {completed.returncode}: {stderr_text}")

    return completed.stdout


# Example usage
if __name__ == "__main__":
    plaintext = b"hello secret bytes"
    print(call_java_for_crypto("enc", plaintext))