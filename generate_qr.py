import qrcode
import uuid
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import os

def creer_badge_stagiaire(nom_stagiaire, id_existant=None):
    """
    Génère un badge PDF. 
    Si id_existant est fourni, il utilise cet ID (ex: depuis Swagger).
    Sinon, il en génère un nouveau.
    """
    # 1. Déterminer l'ID à utiliser
    if id_existant:
        id_unique = id_existant
    else:
        id_unique = str(uuid.uuid4())
    
    # 2. Créer le QR Code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(id_unique)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white")
    
    # Sauvegarde temporaire de l'image
    qr_filename = "temp_qr.png"
    img_qr.save(qr_filename)
    
    # 3. Créer le PDF (Le Badge)
    pdf_filename = f"badge_{nom_stagiaire.replace(' ', '_')}.pdf"
    c = canvas.Canvas(pdf_filename, pagesize=A4)
    
    # Design du badge
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, "PLATEFORME DE STAGE HOSPITALIER - CHU")
    
    c.setFont("Helvetica", 12)
    c.drawString(100, 720, f"STAGIAIRE : {nom_stagiaire.upper()}")
    c.drawString(100, 700, f"ID SYSTEME : {id_unique}")
    
    # Insérer le QR Code
    c.drawImage(qr_filename, 100, 480, width=200, height=200)
    
    # Signature / Note
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(100, 450, "Document officiel - Présentation obligatoire au scan.")
    
    c.showPage()
    c.save()
    
    # Nettoyage
    if os.path.exists(qr_filename):
        os.remove(qr_filename)
        
    print(f"✅ Badge généré avec succès pour : {nom_stagiaire}")
    print(f"🆔 ID utilisé : {id_unique}")
    print(f"📄 Fichier : {pdf_filename}")

# ===========================================================
# CONFIGURATION POUR ABIR FATAH
# ===========================================================

nom_du_stagiaire = "Abir Fatah"
id_officiel_swagger = "7afedc09-4c25-4e8f-b16d-7ce7ee85f0d5"

# Lancement de la génération
creer_badge_stagiaire(nom_du_stagiaire, id_officiel_swagger)