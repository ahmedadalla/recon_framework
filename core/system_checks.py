import shutil
import sys

def verify_dependencies():
    # List of all CLI tools the framework relies on
    required_tools = [
        "subfinder", "puredns", "dnsx", "anew", 
        "nmap", "httpx", "katana", "uro", "gau", "waybackurls", "gf",
        "gowitness", "ffuf", "nuclei", "dalfox", "dnsgen",
        "crlfuzz", "s3scanner"
    ]
    
    missing = [tool for tool in required_tools if not shutil.which(tool)]
    
    if missing:
        print(f"[!] Critical Error: Missing tools in PATH: {', '.join(missing)}")
        print("[*] Please install them or check your ~/.bashrc paths.")
        sys.exit(1)
    
    print("[✓] All system dependencies verified.")
