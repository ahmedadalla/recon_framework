import os
from pathlib import Path
from config import RESULTS_DIR, GEMINI_API_KEY
from core.discord_alert import send_alert

try:
    from fpdf import FPDF
except ImportError:
    FPDF = None

try:
    from google import genai
except ImportError:
    genai = None

def generate_gemini_summary(raw_findings):
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE" or not genai:
        return "AI reporting is currently disabled. Set GEMINI_API_KEY in your environment and install the google-genai package to enable this feature."

    try:
        # Initialize the Gemini Client
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        prompt = f"""
        You are a senior penetration tester and bug bounty hunter. I have run automated security scanners (Nuclei, Dalfox) on a target.
        Analyze these raw findings and write a professional Executive Summary for a penetration testing report.
        
        Rules:
        1. Group similar vulnerabilities together.
        2. Highlight the most critical risks first.
        3. Provide brief, actionable remediation advice.
        4. Keep the tone professional and objective.
        5. DO NOT use markdown formatting like ** or ##, as this will be parsed into a raw PDF. Use standard text spacing.
        
        Raw Automated Findings (Truncated):
        {raw_findings[:5000]} 
        """
        
        # Generate the response using Gemini Flash
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        
        return response.text.strip()
    
    except Exception as e:
        return f"Error generating AI summary: {e}"

def run_reporting(vuln_dir, target_domain):
    print("\n[=== PHASE 6: REPORT GENERATION ===]")
    print("[+] Gathering vulnerability data...")
    
    # 1. Read Vulnerability Data
    raw_text = ""
    nuclei_files = [
        vuln_dir / "nuclei_hosts_results.txt",
        vuln_dir / "nuclei_takeovers_results.txt",
        vuln_dir / "nuclei_focused_results.txt",
        vuln_dir / "nuclei_results.txt",
    ]
    for nuclei_file in nuclei_files:
        if nuclei_file.exists():
            with open(nuclei_file, "r") as f:
                raw_text += f"--- Nuclei Findings ({nuclei_file.name}) ---\n" + f.read() + "\n"

    open_ports_file = RESULTS_DIR / "open_ports.txt"
    if open_ports_file.exists():
        with open(open_ports_file, "r") as f:
            raw_text += "--- Open Ports ---\n" + f.read() + "\n"

    nse_file = vuln_dir / "nse_results.txt"
    if nse_file.exists():
        with open(nse_file, "r") as f:
            raw_text += "--- NSE Findings ---\n" + f.read() + "\n"
            
    dalfox_file = vuln_dir / "dalfox_results.txt"
    if dalfox_file.exists():
        with open(dalfox_file, "r") as f:
            raw_text += "--- Dalfox Findings ---\n" + f.read() + "\n"

    sqlmap_file = vuln_dir / "sqlmap_results.txt"
    if sqlmap_file.exists():
        with open(sqlmap_file, "r") as f:
            raw_text += "--- SQLMap Findings ---\n" + f.read() + "\n"

    crlfuzz_file = vuln_dir / "crlfuzz_results.txt"
    if crlfuzz_file.exists():
        with open(crlfuzz_file, "r") as f:
            raw_text += "--- CRLFuzz Findings ---\n" + f.read() + "\n"

    s3_file = vuln_dir / "s3_results.txt"
    if s3_file.exists():
        with open(s3_file, "r") as f:
            raw_text += "--- S3 Scanner Findings ---\n" + f.read() + "\n"

    routed_dir = vuln_dir / "gf_routed"
    if routed_dir.exists():
        for routed_file in sorted(routed_dir.glob("*.txt")):
            with open(routed_file, "r") as f:
                raw_text += f"--- GF Routed Findings ({routed_file.name}) ---\n" + f.read() + "\n"

    if not raw_text.strip():
        raw_text = "No automated vulnerabilities were detected during this scan phase."

    # 2. Get AI Summary from Gemini
    print("[+] Requesting AI Executive Summary from Gemini...")
    ai_summary = generate_gemini_summary(raw_text)

    # 3. Build PDF (or fallback text report if FPDF is unavailable)
    print("[+] Compiling PDF Report...")
    if FPDF is None:
        txt_report = RESULTS_DIR / f"{target_domain}_Recon_Report.txt"
        with open(txt_report, "w") as f:
            f.write(f"Security Reconnaissance Report: {target_domain}\n")
            f.write("=" * 70 + "\n\n")
            f.write("Executive Summary (AI Generated)\n")
            f.write("-" * 35 + "\n")
            f.write(ai_summary + "\n\n")
            f.write("Automated Scanner Log Snippet\n")
            f.write("-" * 35 + "\n")
            raw_snippet = "\n".join(raw_text.splitlines()[:30])
            if len(raw_text.splitlines()) > 30:
                raw_snippet += "\n\n... (Logs truncated for report readability. See full files in results directory)."
            f.write(raw_snippet + "\n")

        print("[!] FPDF not installed. Generated text report instead of PDF.")
        send_alert("Report Generated (TXT Fallback)", f"Reconnaissance complete! Report saved to {txt_report}", 0x3498db)
        return txt_report

    pdf_path = RESULTS_DIR / f"{target_domain}_Recon_Report.pdf"
    
    pdf = FPDF()
    pdf.add_page()
    
    # Report Title
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, txt=f"Security Reconnaissance Report: {target_domain}", ln=True, align='C')
    pdf.ln(10)
    
    # Executive Summary Section
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, txt="Executive Summary (AI Generated)", ln=True)
    pdf.set_font("Arial", '', 10)
    
    # Clean text to prevent FPDF character encoding crashes
    safe_summary = ai_summary.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 7, txt=safe_summary)
    pdf.ln(10)
    
    # Raw Data Snippet Section
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, txt="Automated Scanner Log Snippet", ln=True)
    pdf.set_font("Courier", '', 8)
    
    raw_snippet = "\n".join(raw_text.splitlines()[:30])
    if len(raw_text.splitlines()) > 30:
        raw_snippet += "\n\n... (Logs truncated for report readability. See full files in results directory)."
        
    safe_raw = raw_snippet.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 5, txt=safe_raw)
    
    # Save the PDF
    pdf.output(str(pdf_path))
    
    print(f"[✓] PDF Report successfully generated at {pdf_path}")
    send_alert("📝 Final Report Generated", f"Reconnaissance complete! PDF Report saved to {pdf_path}", 0x3498db)
    
    return pdf_path
