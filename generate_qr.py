import qrcode
import uuid
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

def creer_badge_stagiaire(nom_stagiaire):
    # 1. Générer un identifiant unique (UUID)
    # C'est ce qui sera scanné à l'hôpital 
    id_unique = str(uuid.uuid4())
    
    # 2. Créer le QR Code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(id_unique)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white")
    
    # Sauvegarder l'image temporairement
    qr_filename = "temp_qr.png"
    img_qr.save(qr_filename)
    
    # 3. Créer le PDF (Le Badge) 
    pdf_filename = f"badge_{nom_stagiaire.replace(' ', '_')}.pdf"
    c = canvas.Canvas(pdf_filename, pagesize=A4)
    
    # Ajouter du texte au PDF
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, "PLATEFORME DE STAGE HOSPITALIER")
    c.setFont("Helvetica", 12)
    c.drawString(100, 730, f"Stagiaire : {nom_stagiaire}")
    c.drawString(100, 715, f"ID : {id_unique}")
    
    # Insérer le QR Code dans le PDF
    c.drawImage(qr_filename, 100, 500, width=200, height=200)
    
    # Finaliser et sauvegarder
    c.showPage()
    c.save()
    print(f"✅ Succès ! Le badge de {nom_stagiaire} est prêt : {pdf_filename}")

# Lancer le test
creer_badge_stagiaire("Nouhaila Touil")