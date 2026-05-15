import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors
import os
import sys

# ── DATABASE IMPORT ───────────────────────────────────────────────────────────
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()
from database import SessionLocal, Intern, Department



# ── BADGE DIMENSIONS (mirrors index.html jsPDF format exactly) ────────────────
#
#  jsPDF uses:  format: [85, 120]  unit: "mm"
#  So the page IS the badge — 85 mm wide × 120 mm tall.
#
#  Section mapping (Y measured from BOTTOM in ReportLab, from TOP in jsPDF):
#
#  jsPDF (top→down, mm)        ReportLab (bottom→up)
#  ──────────────────────────  ──────────────────────
#  [ 0 – 25]  blue header      H-25mm → H
#  [25 – 60]  name + service   H-60mm → H-25mm
#  [62 – 107] QR box 45×45mm   H-107mm → H-62mm
#  [107–120]  UUID footer       0 → H-107mm
#
W = 85  * mm   # page width  in points
H = 120 * mm   # page height in points

# Colours matching index.html exactly
BLUE      = colors.HexColor("#1E88E5")   # rgb(30, 136, 229)
WHITE     = colors.white
DARK      = colors.HexColor("#0a0d12")   # name text
GREY_TEXT = colors.HexColor("#969696")   # service / UUID text
LIGHT_BG  = colors.HexColor("#F5F7FA")   # card background
BORDER    = colors.HexColor("#C8C8C8")   # QR frame border


# ── BADGE GENERATOR ───────────────────────────────────────────────────────────

def creer_badge_pro(nom_stagiaire: str, id_unique: str, service_name: str) -> str:
    """
    Generate a badge PDF sized 85 × 120 mm — identical layout to
    the jsPDF badge produced by index.html.
    Returns the path to the generated PDF.
    """
    pdf_filename = f"badge_{nom_stagiaire.replace(' ', '_')}.pdf"
    c = canvas.Canvas(pdf_filename, pagesize=(W, H))

    # ── BACKGROUND ────────────────────────────────────────────────────────────
    c.setFillColor(LIGHT_BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # ── BLUE HEADER BAND  (top 25 mm) ─────────────────────────────────────────
    header_h = 25 * mm
    c.setFillColor(BLUE)
    c.rect(0, H - header_h, W, header_h, fill=1, stroke=0)

    # "CENTRE HOSPITALIER"  fontSize=12  jsPDF y=12 → RL y = H - 12mm
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(W / 2, H - 12 * mm, "CENTRE HOSPITALIER")

    # "CARTE D'ACCÈS STAGIAIRE"  fontSize=8  jsPDF y=18 → RL y = H - 18mm
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(W / 2, H - 18 * mm, "CARTE D'ACCÈS STAGIAIRE")

    # ── NAME  (jsPDF: fontSize=16, y=45) ──────────────────────────────────────
    name_text = nom_stagiaire.upper()
    font_size = 16
    # Auto-shrink if the name is too wide for the card
    while c.stringWidth(name_text, "Helvetica-Bold", font_size) > W - 8 * mm and font_size > 8:
        font_size -= 1
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", font_size)
    c.drawCentredString(W / 2, H - 45 * mm, name_text)

    # ── SERVICE  (jsPDF: fontSize=10, y=53, grey) ──────────────────────────────
    service_text = f"SERVICE : {service_name.upper()}"
    c.setFillColor(GREY_TEXT)
    c.setFont("Helvetica", 10)

    max_width = W - 8 * mm
    text_width = c.stringWidth(service_text, "Helvetica", 10)

    if text_width <= max_width:
        c.drawCentredString(W / 2, H - 53 * mm, service_text)
    else:
        # Split into 2 lines
        words = service_text.split()
        line1, line2 = "", ""
        for word in words:
            test = (line1 + " " + word).strip()
            if c.stringWidth(test, "Helvetica", 10) <= max_width:
                line1 = test
            else:
                line2 = (line2 + " " + word).strip()
        c.drawCentredString(W / 2, H - 50 * mm, line1)
        c.drawCentredString(W / 2, H - 55 * mm, line2)

    # ── QR CODE FRAME  (jsPDF: rect(20, 62, 45, 45)) ──────────────────────────
    #  In jsPDF coords: x=20mm, y_top=62mm, w=45mm, h=45mm
    #  ReportLab y_bottom = H - (62 + 45)mm = H - 107mm
    frame_x = 20 * mm
    frame_y = H - 107 * mm
    frame_s = 45 * mm

    c.setStrokeColor(BORDER)
    c.setLineWidth(0.5)
    c.rect(frame_x, frame_y, frame_s, frame_s, fill=0, stroke=1)

    # QR image inside frame  (jsPDF: addImage at 22.5, 64.5, size 40×40)
    qr_margin = 2.5 * mm
    qr_size   = 40 * mm
    qr_x = frame_x + qr_margin
    qr_y = frame_y + qr_margin

    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(id_unique)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="#0a0d12", back_color="white")

    qr_temp = f"temp_qr_{id_unique[:8]}.png"
    img_qr.save(qr_temp)
    c.drawImage(qr_temp, qr_x, qr_y, width=qr_size, height=qr_size)
    os.remove(qr_temp)

    # ── UUID FOOTER  (jsPDF: fontSize=7, y=114, light grey) ───────────────────
    c.setFillColor(GREY_TEXT)
    c.setFont("Helvetica", 7)
    c.drawCentredString(W / 2, H - 114 * mm, f"UUID: {id_unique}")

    c.showPage()
    c.save()
    return pdf_filename


# ── DB HELPERS ────────────────────────────────────────────────────────────────
# Each helper opens its OWN session, fetches what it needs as plain dicts,
# then closes immediately — so a dropped SSL connection never kills a loop.

def _fetch_all_interns() -> list[dict]:
    """Return all interns as plain dicts (no live ORM objects)."""
    db = SessionLocal()
    try:
        rows = (
            db.query(Intern, Department.name)
            .join(Department, Intern.department_id == Department.id)
            .all()
        )
        return [
            {
                "id":         intern.id,
                "first_name": intern.first_name,
                "last_name":  intern.last_name,
                "dept_name":  dept_name,
            }
            for intern, dept_name in rows
        ]
    finally:
        db.close()


def _fetch_intern_by_uuid(uid: str) -> dict | None:
    """Return one intern as a plain dict, or None if not found."""
    db = SessionLocal()
    try:
        row = (
            db.query(Intern, Department.name)
            .join(Department, Intern.department_id == Department.id)
            .filter(Intern.id == uid.strip())
            .first()
        )
        if row is None:
            return None
        intern, dept_name = row
        return {
            "id":         intern.id,
            "first_name": intern.first_name,
            "last_name":  intern.last_name,
            "dept_name":  dept_name,
        }
    finally:
        db.close()


# ── MENU ──────────────────────────────────────────────────────────────────────

def print_header():
    print("\n" + "═" * 50)
    print("   CHU · Générateur de Badges QR Code")
    print("═" * 50)


def generate_for_row(row: dict):
    nom_complet = f"{row['first_name']} {row['last_name']}"
    pdf_path = creer_badge_pro(nom_complet, row["id"], row["dept_name"])
    print(f"  ✅  Badge généré → {pdf_path}")


def menu_all():
    # Fetch everything in ONE short-lived session, then close it before looping
    interns = _fetch_all_interns()
    if not interns:
        print("\n⚠️  Aucun stagiaire trouvé dans la base.")
        return
    print(f"\n🖨️  Génération de {len(interns)} badge(s)...\n")
    for row in interns:
        generate_for_row(row)
    print(f"\n✅  {len(interns)} badge(s) générés avec succès !")


def menu_specific():
    print("\nEntrez les UUID des stagiaires (un par ligne).")
    print("Laissez une ligne vide pour terminer.\n")
    uuids = []
    while True:
        entry = input("  UUID : ").strip()
        if not entry:
            break
        uuids.append(entry)

    if not uuids:
        print("⚠️  Aucun UUID saisi.")
        return

    print(f"\n🖨️  Génération de {len(uuids)} badge(s)...\n")
    not_found, generated = [], 0
    for uid in uuids:
        # Each lookup opens + closes its own connection — SSL drop = one failure max
        row = _fetch_intern_by_uuid(uid)
        if row is None:
            print(f"  ❌  UUID introuvable : {uid}")
            not_found.append(uid)
        else:
            generate_for_row(row)
            generated += 1

    print(f"\n✅  {generated} badge(s) générés.")
    if not_found:
        print(f"⚠️  {len(not_found)} UUID(s) introuvable(s) : {', '.join(not_found)}")


def menu_list():
    interns = _fetch_all_interns()
    if not interns:
        print("\n⚠️  Aucun stagiaire trouvé dans la base.")
        return
    print(f"\n{'Nom':<30} {'Service':<20} {'UUID'}")
    print("─" * 90)
    for row in interns:
        nom = f"{row['first_name']} {row['last_name']}"
        print(f"{nom:<30} {row['dept_name']:<20} {row['id']}")


def main():
    while True:
        print_header()
        print("  [1]  Générer TOUS les badges")
        print("  [2]  Générer des badges spécifiques (par UUID)")
        print("  [3]  Lister les stagiaires et leurs UUID")
        print("  [0]  Quitter")
        print()
        choice = input("  Votre choix : ").strip()

        if choice == "1":
            menu_all()
        elif choice == "2":
            menu_specific()
        elif choice == "3":
            menu_list()
        elif choice == "0":
            print("\n👋 Au revoir !\n")
            break
        else:
            print("\n⚠️  Choix invalide. Veuillez entrer 0, 1, 2 ou 3.")


if __name__ == "__main__":
    main()