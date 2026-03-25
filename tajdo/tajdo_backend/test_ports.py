import socket

host = "imap.universal-domains.de"
ports = [993, 143]

print(f"--- Checking connectivity to {host} ---")

for port in ports:
    print(f"Testing Port {port}...", end=" ")
    try:
        # Try to open a basic TCP connection
        sock = socket.create_connection((host, port), timeout=5)
        print("OPEN ✅")
        sock.close()
    except Exception as e:
        print(f"CLOSED or BLOCKED ❌ ({e})")
        
print("---------------------------------------")
print("If Port 993 is OPEN: The issue is likely Antivirus or SSL versions.")
print("If Port 143 is OPEN and 993 is CLOSED: We need to update the code to use STARTTLS.")