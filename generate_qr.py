import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
import os

def creer_badge_pro(nom_stagiaire, id_unique, id_service):
    pdf_filename = f"badge_{nom_stagiaire.replace(' ', '_')}.pdf"
    c = canvas.Canvas(pdf_filename, pagesize=A4)
    
    # --- Dimensions et Cadre ---
    width, height = 250, 380
    x_start, y_start = 170, 400
    c.setStrokeColor(colors.dodgerblue)
    c.setLineWidth(3)
    c.roundRect(x_start, y_start, width, height, 10, fill=0)
    
    # --- Bandeau Supérieur ---
    c.setFillColor(colors.dodgerblue)
    c.roundRect(x_start, y_start + height - 50, width, 50, 10, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(x_start + width/2, y_start + height - 30, "CENTRE HOSPITALIER")

    # --- Nom du Stagiaire ---
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(x_start + width/2, y_start + height - 90, nom_stagiaire.upper())
    
    # --- AFFICHAGE DE L'ID SERVICE ---
    c.setFont("Helvetica-Bold", 13)
    c.setFillColor(colors.black)
    c.drawCentredString(x_start + width/2, y_start + height - 115, f"SERVICE ID : {id_service}")

    # --- QR Code ---
    qr = qrcode.QRCode(box_size=4, border=2)
    qr.add_data(id_unique)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white")
    
    qr_temp = "temp_qr.png"
    img_qr.save(qr_temp)
    c.drawImage(qr_temp, x_start + 50, y_start + 100, width=150, height=150)

    # --- Pied de Badge ---
    c.setFillColor(colors.grey)
    c.setFont("Helvetica", 7)
    c.drawCentredString(x_start + width/2, y_start + 45, f"UUID: {id_unique}")
    
    c.setFillColor(colors.dodgerblue)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(x_start + width/2, y_start + 20, "SCAN POUR POINTAGE")

    c.showPage()
    c.save()
    os.remove(qr_temp)
    print(f"✅ Badge généré pour {nom_stagiaire} (Service {id_service})")

# --- EXEMPLE D'UTILISATION ---
# Tu mets ici l'ID du département (1, 2 ou 3) que tu as configuré dans ta base
creer_badge_pro("Nouhaila Touil", "79381cc2-d663-4477-a5d7-3d4902b8a0ed", 5)