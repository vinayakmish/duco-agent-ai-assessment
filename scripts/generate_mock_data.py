"""Generate realistic mock medical documents for DuCO-Agent testing.

Creates:
1. priya_pt_invoice.png — Scanned PT invoice with handwritten notes
2. aarav_mri_report.pdf — MRI radiology report (PDF)
3. surgeon_estimate.jpg — Surgeon's billing estimate image

Uses only Pillow and reportlab (no external fonts required).
"""
import os
import random
import math
from PIL import Image, ImageDraw, ImageFont

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def _get_font(size: int, bold: bool = False, italic: bool = False):
    """Get a font, falling back to default if system fonts unavailable."""
    font_names = []
    if bold and italic:
        font_names = ["arialbi.ttf", "timesbi.ttf", "calibriz.ttf"]
    elif bold:
        font_names = ["arialbd.ttf", "timesbd.ttf", "calibrib.ttf"]
    elif italic:
        font_names = ["ariali.ttf", "timesi.ttf", "calibrii.ttf"]
    else:
        font_names = ["arial.ttf", "times.ttf", "calibri.ttf"]

    for name in font_names:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def _add_scan_noise(image: Image.Image) -> Image.Image:
    """Add subtle noise to simulate a scanned document."""
    pixels = image.load()
    width, height = image.size
    for _ in range(int(width * height * 0.002)):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        r, g, b = pixels[x, y]
        noise = random.randint(-20, 20)
        pixels[x, y] = (
            max(0, min(255, r + noise)),
            max(0, min(255, g + noise)),
            max(0, min(255, b + noise)),
        )
    return image


def generate_pt_invoice():
    """Generate Priya's Physical Therapy invoice as a scanned PNG."""
    width, height = 800, 1100
    # Off-white background for "scanned" effect
    img = Image.new("RGB", (width, height), (252, 248, 240))
    draw = ImageDraw.Draw(img)

    font_large = _get_font(24, bold=True)
    font_medium = _get_font(16)
    font_medium_bold = _get_font(16, bold=True)
    font_small = _get_font(13)
    font_italic = _get_font(14, italic=True)

    y = 40

    # Clinic Letterhead
    draw.text((width // 2 - 180, y), "PhysioFirst Rehabilitation Clinic",
              fill=(0, 80, 130), font=font_large)
    y += 35
    draw.text((width // 2 - 160, y),
              "42, Linking Road, Bandra West, Mumbai - 400050",
              fill=(60, 60, 60), font=font_small)
    y += 20
    draw.text((width // 2 - 120, y),
              "Tel: +91-22-2640-5500 | GSTIN: 27AABCP1234F1ZP",
              fill=(60, 60, 60), font=font_small)
    y += 30
    draw.line([(40, y), (width - 40, y)], fill=(0, 80, 130), width=2)
    y += 20

    # Invoice Header
    draw.text((50, y), "INVOICE", fill=(0, 0, 0), font=font_large)
    draw.text((550, y), "Invoice No: PFC/2024/0347", fill=(80, 80, 80), font=font_small)
    y += 25
    draw.text((550, y), "Date: 28-Mar-2024", fill=(80, 80, 80), font=font_small)
    y += 35

    # Patient Details
    draw.text((50, y), "Patient Name:", fill=(0, 0, 0), font=font_medium_bold)
    draw.text((200, y), "Mrs. Priya Sen", fill=(0, 0, 0), font=font_medium)
    y += 25
    draw.text((50, y), "Patient ID:", fill=(0, 0, 0), font=font_medium_bold)
    draw.text((200, y), "PFC-PT-2024-0891", fill=(0, 0, 0), font=font_medium)
    y += 25
    draw.text((50, y), "Referring Dr:", fill=(0, 0, 0), font=font_medium_bold)
    draw.text((200, y), "Dr. Ananya Sharma, MBBS, MD (PMR)",
              fill=(0, 0, 0), font=font_medium)
    y += 25
    draw.text((50, y), "Diagnosis:", fill=(0, 0, 0), font=font_medium_bold)
    draw.text((200, y), "Chronic lower back pain", fill=(0, 0, 0), font=font_medium)
    y += 35
    draw.line([(40, y), (width - 40, y)], fill=(180, 180, 180), width=1)
    y += 15

    # Table Header
    headers = ["S.No", "Description", "Date(s)", "Qty", "Amount (Rs.)"]
    col_x = [50, 100, 430, 570, 650]
    for i, header in enumerate(headers):
        draw.text((col_x[i], y), header, fill=(0, 0, 0), font=font_medium_bold)
    y += 25
    draw.line([(40, y), (width - 40, y)], fill=(180, 180, 180), width=1)
    y += 10

    # Line Items - NO CPT codes (agent must infer)
    items = [
        ("1", "Physical Therapy Evaluation\n- Initial Assessment", "04-Mar-2024", "1", "5,000"),
        ("2", "Therapeutic Exercise\n- Strength & flexibility training\n- Core stabilization",
         "06,11,13,18,\n20,25-Mar-2024", "6", "25,000"),
    ]
    for item in items:
        line_y = y
        for i, val in enumerate(item):
            lines = val.split("\n")
            for j, line in enumerate(lines):
                draw.text((col_x[i], line_y + j * 18), line,
                          fill=(0, 0, 0), font=font_small)
        y += len(max(item, key=lambda x: len(x.split("\n"))).split("\n")) * 18 + 15

    y += 10
    draw.line([(40, y), (width - 40, y)], fill=(180, 180, 180), width=1)
    y += 10

    # Total
    draw.text((500, y), "TOTAL:", fill=(0, 0, 0), font=font_medium_bold)
    draw.text((630, y), "Rs. 30,000/-", fill=(0, 0, 0), font=font_medium_bold)
    y += 25
    draw.text((450, y), "(Rupees Thirty Thousand Only)",
              fill=(80, 80, 80), font=font_small)
    y += 40

    # Handwritten-style notes (italic font to simulate handwriting)
    draw.line([(40, y), (width - 40, y)], fill=(180, 180, 180), width=1)
    y += 15
    draw.text((50, y), "Billing Notes (handwritten):",
              fill=(100, 100, 100), font=font_small)
    y += 22
    # Simulate handwritten text with blue "ink" color
    draw.text((60, y), "- Chronic lower back pain - ongoing treatment since Jan 2024",
              fill=(0, 40, 160), font=font_italic)
    y += 22
    draw.text((60, y), "- Patient requires continued PT sessions",
              fill=(0, 40, 160), font=font_italic)
    y += 22
    draw.text((60, y), "- Payment Status: Pending Insurance Claim",
              fill=(0, 40, 160), font=font_italic)
    y += 40

    # Authorized signature area
    draw.text((500, y), "Authorized Signatory", fill=(80, 80, 80), font=font_small)
    y += 5
    draw.line([(490, y), (720, y)], fill=(0, 0, 0), width=1)
    y += 15
    draw.text((510, y), "PhysioFirst Rehab Clinic",
              fill=(80, 80, 80), font=font_small)

    # Add scan noise
    img = _add_scan_noise(img)

    # Slight rotation to simulate imperfect scan
    img = img.rotate(0.5, fillcolor=(252, 248, 240), expand=False)

    os.makedirs(DATA_DIR, exist_ok=True)
    img.save(os.path.join(DATA_DIR, "priya_pt_invoice.png"), quality=92)
    print("✓ Generated: data/priya_pt_invoice.png")


def generate_mri_report():
    """Generate Aarav's MRI radiology report as a PDF."""
    if not REPORTLAB_AVAILABLE:
        print("✗ reportlab not installed. Skipping MRI report PDF generation.")
        return

    os.makedirs(DATA_DIR, exist_ok=True)
    pdf_path = os.path.join(DATA_DIR, "aarav_mri_report.pdf")
    c = canvas.Canvas(pdf_path, pagesize=A4)
    w, h = A4

    # Hospital Header
    c.setFillColor(HexColor("#004080"))
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(w / 2, h - 50, "Mumbai Ortho Center")
    c.setFont("Helvetica", 10)
    c.setFillColor(HexColor("#333333"))
    c.drawCentredString(w / 2, h - 65, "Department of Radiology & Diagnostic Imaging")
    c.drawCentredString(w / 2, h - 78,
                        "15, Turner Road, Bandra West, Mumbai - 400050 | Tel: +91-22-2655-8800")

    # Line separator
    c.setStrokeColor(HexColor("#004080"))
    c.setLineWidth(2)
    c.line(40, h - 90, w - 40, h - 90)

    # Report Title
    c.setFillColor(HexColor("#000000"))
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w / 2, h - 115, "MRI RADIOLOGY REPORT")

    y = h - 145

    # Patient Info
    info_lines = [
        ("Patient Name:", "Aarav Sen"),
        ("Age / Gender:", "37 years / Male"),
        ("Date of Birth:", "22/07/1986"),
        ("MRD No:", "MOC-2024-MR-04521"),
        ("Referring Physician:", "Dr. Rajesh Patel, MS Ortho"),
        ("Study:", "MRI Right Knee without contrast"),
        ("Date of Study:", "15-Apr-2024"),
        ("Date of Report:", "16-Apr-2024"),
    ]

    c.setFont("Helvetica-Bold", 10)
    for label, value in info_lines:
        c.drawString(50, y, label)
        c.setFont("Helvetica", 10)
        c.drawString(200, y, value)
        c.setFont("Helvetica-Bold", 10)
        y -= 16

    y -= 10
    c.setStrokeColor(HexColor("#CCCCCC"))
    c.setLineWidth(0.5)
    c.line(40, y, w - 40, y)
    y -= 20

    # Clinical History
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "CLINICAL HISTORY:")
    y -= 16
    c.setFont("Helvetica", 10)
    history = (
        "37-year-old male presenting with acute right knee pain and instability "
        "following a sports injury (football) sustained 2 weeks ago. Patient reports "
        "giving way of the knee and difficulty bearing weight. Clinical examination "
        "reveals positive Lachman test and anterior drawer sign."
    )
    for line in _wrap_text(history, 90):
        c.drawString(50, y, line)
        y -= 14
    y -= 10

    # Technique
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "TECHNIQUE:")
    y -= 16
    c.setFont("Helvetica", 10)
    c.drawString(50, y,
                 "MRI of the right knee performed on 1.5T MRI scanner using standard knee coil.")
    y -= 14
    c.drawString(50, y,
                 "Sequences: Sagittal PD, Sagittal T2 FS, Coronal PD, Coronal T2 FS, Axial PD FS.")
    y -= 20

    # Findings
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "FINDINGS:")
    y -= 16
    c.setFont("Helvetica", 10)

    findings = (
        "There is complete disruption of the anterior cruciate ligament (ACL) fibers "
        "consistent with a full-thickness tear. The ACL shows abnormal signal intensity "
        "with discontinuity of fibers near the femoral attachment. There is associated "
        "bone marrow edema in the lateral femoral condyle and posterior tibial plateau "
        "suggesting a pivot-shift mechanism of injury."
    )
    for line in _wrap_text(findings, 90):
        c.drawString(50, y, line)
        y -= 14
    y -= 5

    findings2 = (
        "The medial meniscus demonstrates a complex tear involving the posterior horn "
        "with extension to the inferior articular surface. The tear extends through "
        "the body of the meniscus with associated meniscal extrusion of approximately 3mm."
    )
    for line in _wrap_text(findings2, 90):
        c.drawString(50, y, line)
        y -= 14
    y -= 5

    additional = [
        "The posterior cruciate ligament (PCL) appears intact with normal signal intensity.",
        "The medial and lateral collateral ligaments are intact.",
        "The lateral meniscus appears normal.",
        "Mild to moderate joint effusion is noted.",
        "The articular cartilage shows no significant focal defects.",
        "The extensor mechanism and patellar tendon appear normal.",
        "The popliteal vessels appear normal.",
    ]
    for line in additional:
        c.drawString(50, y, f"• {line}")
        y -= 14
    y -= 15

    # Impression
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "IMPRESSION:")
    y -= 16
    c.setFont("Helvetica", 10)
    impressions = [
        "1. Complete ACL tear, right knee (full-thickness disruption at femoral attachment).",
        "2. Complex medial meniscus tear, posterior horn, with meniscal extrusion.",
        "3. Bone marrow contusion pattern consistent with pivot-shift injury mechanism.",
        "4. Mild to moderate joint effusion.",
        "5. PCL, collateral ligaments, and lateral meniscus — intact.",
    ]
    for imp in impressions:
        c.drawString(50, y, imp)
        y -= 14
    y -= 10

    # Recommendation
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "RECOMMENDATION:")
    y -= 16
    c.setFont("Helvetica", 10)
    c.drawString(50, y,
                 "Clinical correlation and orthopedic surgical consultation recommended.")
    c.drawString(50, y - 14,
                 "ACL reconstruction with concurrent meniscal repair should be considered.")
    y -= 40

    # Radiologist
    c.setStrokeColor(HexColor("#CCCCCC"))
    c.line(40, y, w - 40, y)
    y -= 25
    c.setFont("Helvetica-Bold", 10)
    c.drawString(400, y, "Dr. Meera Krishnamurthy")
    y -= 14
    c.setFont("Helvetica", 9)
    c.drawString(400, y, "MD Radiology, FRCR (UK)")
    y -= 12
    c.drawString(400, y, "Consultant Radiologist")
    y -= 12
    c.drawString(400, y, "Mumbai Ortho Center")

    # Disclaimer
    y -= 30
    c.setFont("Helvetica", 7)
    c.setFillColor(HexColor("#888888"))
    c.drawCentredString(w / 2, y,
                        "This report is electronically generated and does not require a physical signature.")
    c.drawCentredString(w / 2, y - 10,
                        "The findings are based on the images provided and should be correlated clinically.")

    c.save()
    print("✓ Generated: data/aarav_mri_report.pdf")


def generate_surgeon_estimate():
    """Generate surgeon's billing estimate as a JPG image."""
    width, height = 800, 900
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    font_large = _get_font(22, bold=True)
    font_medium = _get_font(15)
    font_medium_bold = _get_font(15, bold=True)
    font_small = _get_font(12)
    font_small_bold = _get_font(12, bold=True)

    y = 35

    # Doctor Header
    draw.text((width // 2 - 180, y), "Dr. Vikram Mehta",
              fill=(0, 60, 120), font=font_large)
    y += 30
    draw.text((width // 2 - 200, y),
              "MS (Orthopaedics), DNB, Fellowship in Sports Medicine",
              fill=(80, 80, 80), font=font_small)
    y += 18
    draw.text((width // 2 - 100, y), "Mumbai Ortho Center",
              fill=(80, 80, 80), font=font_small)
    y += 18
    draw.text((width // 2 - 170, y),
              "15, Turner Road, Bandra West, Mumbai - 400050",
              fill=(80, 80, 80), font=font_small)
    y += 25
    draw.line([(40, y), (width - 40, y)], fill=(0, 60, 120), width=2)
    y += 20

    # Title
    draw.text((width // 2 - 120, y), "SURGICAL COST ESTIMATE",
              fill=(0, 0, 0), font=font_medium_bold)
    y += 30

    # Patient Info
    info = [
        ("Patient Name:", "Mr. Aarav Sen"),
        ("Age / Gender:", "37 years / Male"),
        ("Date:", "10-May-2024"),
        ("Diagnosis:", "Complete ACL Tear + Medial Meniscus Tear, Right Knee"),
        ("Proposed Surgery:", "ACL Reconstruction with Meniscal Repair"),
        ("Estimated Surgery Date:", "To be scheduled post insurance pre-authorization"),
    ]
    for label, value in info:
        draw.text((50, y), label, fill=(0, 0, 0), font=font_medium_bold)
        draw.text((250, y), value, fill=(0, 0, 0), font=font_medium)
        y += 22
    y += 15

    # Table Header
    draw.rectangle([(40, y), (width - 40, y + 28)], fill=(0, 60, 120))
    headers = ["Code", "Description", "Est. Cost (INR)"]
    header_x = [55, 160, 600]
    for i, header in enumerate(headers):
        draw.text((header_x[i], y + 5), header,
                  fill=(255, 255, 255), font=font_medium_bold)
    y += 28

    # Table Rows
    rows = [
        ("CPT 29888", "Arthroscopically Aided Anterior Cruciate\nLigament Repair/Augmentation/Reconstruction",
         "3,50,000"),
        ("CPT 29881", "Arthroscopy, Knee, Surgical; with Meniscectomy\nincl. any Meniscal Shaving",
         "1,00,000"),
    ]
    for code, desc, cost in rows:
        row_h = len(desc.split("\n")) * 18 + 12
        draw.line([(40, y), (width - 40, y)], fill=(200, 200, 200), width=1)
        draw.text((55, y + 6), code, fill=(0, 0, 0), font=font_medium_bold)
        desc_lines = desc.split("\n")
        for j, line in enumerate(desc_lines):
            draw.text((160, y + 6 + j * 18), line, fill=(0, 0, 0), font=font_small)
        draw.text((620, y + 6), f"Rs. {cost}", fill=(0, 0, 0), font=font_medium)
        y += row_h

    draw.line([(40, y), (width - 40, y)], fill=(0, 60, 120), width=2)
    y += 8

    # Total
    draw.text((450, y), "TOTAL ESTIMATED COST:", fill=(0, 0, 0), font=font_medium_bold)
    y += 22
    draw.text((500, y), "Rs. 4,50,000/-", fill=(0, 60, 120), font=font_large)
    y += 22
    draw.text((450, y), "(Rupees Four Lakhs Fifty Thousand Only)",
              fill=(80, 80, 80), font=font_small)
    y += 35

    # Notes
    draw.line([(40, y), (width - 40, y)], fill=(200, 200, 200), width=1)
    y += 10
    draw.text((50, y), "Important Notes:", fill=(0, 0, 0), font=font_medium_bold)
    y += 22
    notes = [
        "1. Pre-authorization required from insurance provider prior to scheduling.",
        "2. Above costs are estimates; actual charges may vary based on intra-operative findings.",
        "3. Additional costs for anaesthesia, hospital stay, and post-op care are separate.",
        "4. Hospital stay estimated: 2-3 days.",
    ]
    for note in notes:
        draw.text((60, y), note, fill=(60, 60, 60), font=font_small)
        y += 18
    y += 25

    # Surgeon signature
    draw.text((500, y), "Dr. Vikram Mehta", fill=(0, 0, 0), font=font_medium_bold)
    y += 18
    draw.text((500, y), "MS Ortho, Sports Medicine", fill=(80, 80, 80), font=font_small)
    y += 15
    draw.text((500, y), "Reg. No: MMC/2008/12345", fill=(80, 80, 80), font=font_small)

    os.makedirs(DATA_DIR, exist_ok=True)
    img.save(os.path.join(DATA_DIR, "surgeon_estimate.jpg"), quality=90)
    print("✓ Generated: data/surgeon_estimate.jpg")


def _wrap_text(text: str, max_chars: int) -> list[str]:
    """Word-wrap text to a maximum character width."""
    words = text.split()
    lines = []
    current_line = []
    current_len = 0
    for word in words:
        if current_len + len(word) + 1 > max_chars:
            lines.append(" ".join(current_line))
            current_line = [word]
            current_len = len(word)
        else:
            current_line.append(word)
            current_len += len(word) + 1
    if current_line:
        lines.append(" ".join(current_line))
    return lines


if __name__ == "__main__":
    print("Generating mock medical documents for DuCO-Agent...")
    print()
    generate_pt_invoice()
    generate_mri_report()
    generate_surgeon_estimate()
    print()
    print("All mock documents generated in data/ directory.")
