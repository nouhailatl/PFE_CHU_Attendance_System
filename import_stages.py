"""
import_stages.py — Import des fichiers Excel de stage CHU
==========================================================

Lit les 46 fichiers Excel (3ème→6ème année, toutes spécialités),
extrait les étudiants et leurs périodes de stage, et peuple :
  - departments  (noms réels des services)
  - interns      (1 ligne par étudiant unique, identifié par CNE)
  - rotations    (1 ligne par étudiant × service × période)

Usage :
    python import_stages.py                          # chemin par défaut
    python import_stages.py /chemin/vers/dossier     # chemin custom

Le script est IDEMPOTENT : relancer n'écrase pas les données,
il met à jour si nécessaire (upsert basé sur le CNE).

Structure attendue des fichiers :
    Dossier racine/
        3 EME ANNEE/    ← annee = 3
        4 EME ANNEE/    ← annee = 4
        5EME ANNEE/     ← annee = 5
        6 EME ANNEE/    ← annee = 6

Chaque fichier contient :
    Ligne "SERVICE : NomService"
    Ligne "PERIODE X : du JJ/MM/AAAA au JJ/MM/AAAA"
    Ligne header : Groupe | N° APOGEE | NOM | PRENOM | NOTE | DECISION
    Lignes données : G1 | 22018916 | JOUIHRI | DOUAE | ...
"""

from dotenv import load_dotenv
load_dotenv()

import os
import re
import sys
import uuid
import glob
from datetime import datetime, date

import openpyxl
from sqlalchemy.orm import Session
from database import SessionLocal, Intern, Department

# ── Modèle Rotation (import local pour éviter la dépendance circulaire) ───────
from sqlalchemy import Column, String, Integer, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base
from database import Base, engine

class Rotation(Base):
    __tablename__ = "rotations"
    id            = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    intern_id     = Column(String, ForeignKey("interns.id", ondelete="CASCADE"), nullable=False)
    department_id = Column(String, ForeignKey("departments.id"), nullable=False)
    periode_num   = Column(Integer, nullable=False)
    date_debut    = Column(Date, nullable=False)
    date_fin      = Column(Date, nullable=False)
    annee_univ    = Column(String, default="2025-2026")
    __table_args__ = (
        UniqueConstraint("intern_id", "department_id", "periode_num", "annee_univ",
                         name="uq_rotation"),
    )

Base.metadata.create_all(bind=engine)


# ── Helpers ───────────────────────────────────────────────────────────────────

def detect_year(folder_name: str) -> int | None:
    """Détecte l'année d'études depuis le nom du dossier."""
    name = folder_name.upper()
    if "6" in name:  return 6
    if "5" in name:  return 5
    if "4" in name:  return 4
    if "3" in name:  return 3
    return None


def parse_date(s: str) -> date | None:
    """Parse une date JJ/MM/AAAA ou MM/AAAA."""
    if not s:
        return None
    s = s.strip()
    for fmt in ("%d/%m/%Y", "%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def extract_dates_from_row(row: tuple) -> tuple[int | None, date | None, date | None, date | None, date | None]:
    """
    Extrait le numéro de période et les dates depuis une ligne.
    Certaines périodes ont deux plages (vacances au milieu) :
      PERIODE 3 : du 24/12/2025 au 16/01/2026 | Et 17/02/2026 au 02/03/2026
    Dans ce cas, date_debut = début plage 1, date_fin = fin plage 2.
    Retourne (periode_num, date_debut, date_fin, date_debut2, date_fin2)
    """
    full_text = " ".join(str(c) for c in row if c is not None)

    # Numéro de période
    m = re.search(r'PERIODE\s+(\d)', full_text, re.IGNORECASE)
    if not m:
        return None, None, None, None, None
    periode_num = int(m.group(1))

    # Toutes les dates dans la ligne
    date_matches = re.findall(r'\d{1,2}/\d{1,2}/\d{4}', full_text)
    dates = [parse_date(d) for d in date_matches]
    dates = [d for d in dates if d]

    if len(dates) >= 4:
        return periode_num, dates[0], dates[1], dates[2], dates[3]
    elif len(dates) >= 2:
        return periode_num, dates[0], dates[1], None, None
    elif len(dates) == 1:
        return periode_num, dates[0], None, None, None
    return periode_num, None, None, None, None


def clean_cne(raw: any) -> str | None:
    """Nettoie et valide un N° APOGEE."""
    if raw is None:
        return None
    s = str(raw).strip().replace('\t', '').replace(' ', '')
    # Numérique 7-9 chiffres, ou lettre + 7-9 chiffres (étudiants étrangers)
    if re.match(r'^[A-Za-z]?\d{7,9}$', s):
        return s.upper()
    return None


def clean_name(raw: any) -> str:
    if raw is None:
        return ""
    return str(raw).strip().title()


def get_or_create_department(db: Session, name: str, dept_cache: dict) -> str:
    """Retourne l'id du département, le crée si nécessaire."""
    key = name.lower().strip()
    if key in dept_cache:
        return dept_cache[key]

    existing = db.query(Department).filter(
        Department.name.ilike(name.strip())
    ).first()
    if existing:
        dept_cache[key] = existing.id
        return existing.id

    new_dept = Department(id=str(uuid.uuid4()), name=name.strip())
    db.add(new_dept)
    db.flush()
    dept_cache[key] = new_dept.id
    return new_dept.id


def get_or_create_intern(db: Session, cne: str, first_name: str, last_name: str,
                          annee: int, groupe: str, dept_id: str,
                          intern_cache: dict) -> str:
    """Retourne l'id de l'intern, le crée ou met à jour si nécessaire."""
    if cne in intern_cache:
        return intern_cache[cne]

    existing = db.query(Intern).filter(Intern.cne == cne).first()
    if existing:
        # Mise à jour des champs manquants
        if not existing.annee and annee:
            existing.annee = annee
        if not existing.groupe and groupe:
            existing.groupe = groupe
        db.flush()
        intern_cache[cne] = existing.id
        return existing.id

    new_id = str(uuid.uuid4())
    new_intern = Intern(
        id=new_id,
        first_name=first_name,
        last_name=last_name,
        department_id=dept_id,
        cne=cne,
        annee=annee,
        groupe=groupe,
    )
    db.add(new_intern)
    db.flush()
    intern_cache[cne] = new_id
    return new_id


def upsert_rotation(db: Session, intern_id: str, dept_id: str,
                    periode_num: int, date_debut: date, date_fin: date,
                    annee_univ: str = "2025-2026") -> bool:
    
    existing = db.query(Rotation).filter(
        Rotation.intern_id     == intern_id,
        Rotation.department_id == dept_id,
        Rotation.periode_num   == periode_num,
        Rotation.annee_univ    == annee_univ,
    ).first()

    if existing:
        return False  # déjà là, on skip silencieusement

    try:
        db.add(Rotation(
            id=str(uuid.uuid4()),
            intern_id=intern_id,
            department_id=dept_id,
            periode_num=periode_num,
            date_debut=date_debut,
            date_fin=date_fin,
            annee_univ=annee_univ,
        ))
        db.flush()   # ← flush immédiat pour détecter le doublon avant le commit
        return True
    except Exception:
        db.rollback()  # ← annule juste cette ligne, pas tout le fichier
        return False

# ── Parseur principal d'un fichier Excel ──────────────────────────────────────

def parse_file(filepath: str, annee: int) -> dict:
    """
    Retourne un dict avec :
      service_name : str
      periodes     : list[{num, debut, fin}]
      students     : list[{cne, nom, prenom, groupe, periode_num}]
    """
    wb = openpyxl.load_workbook(filepath, data_only=True)
    ws = wb.active

    result = {"service_name": None, "periodes": [], "students": []}

    current_periode = None
    current_groupe  = None
    header_found    = False

    for row in ws.iter_rows(values_only=True):
        row_text = " ".join(str(c) for c in row if c is not None)

        # ── Nom du service ─────────────────────────────────────────────────
        if "SERVICE" in row_text.upper() and result["service_name"] is None:
            for cell in row:
                if cell and "SERVICE" in str(cell).upper():
                    name = re.sub(r'SERVICE\s*[\xa0:]+\s*', '', str(cell),
                                  flags=re.IGNORECASE).strip()
                    if name:
                        result["service_name"] = name
                    break

        # ── Ligne de période ───────────────────────────────────────────────
        if re.search(r'PERIODE\s+\d', row_text, re.IGNORECASE):
            pnum, d1, d2, d3, d4 = extract_dates_from_row(row)
            if pnum:
                # Période avec deux plages (ex: période 3 avec vacances)
                if d1 and d2:
                    fin_effective = d4 if d4 else d2
                    result["periodes"].append({
                        "num": pnum, "debut": d1, "fin": fin_effective
                    })
                else:
                    result["periodes"].append({
                        "num": pnum, "debut": d1, "fin": None
                    })
                current_periode = pnum
                header_found    = False
            continue

        # ── Ligne header étudiant ──────────────────────────────────────────
        if "N° APOGEE" in row_text or "APOGEE" in row_text.upper():
            header_found = True
            continue

        # ── Ligne données étudiant ─────────────────────────────────────────
        if header_found and current_periode is not None:
            # Détecter nouveau groupe (ex: "G1", "G3 1C", "G5")
            groupe_candidate = None
            for cell in row:
                if cell and re.match(r'^G\d', str(cell).strip(), re.IGNORECASE):
                    groupe_candidate = str(cell).strip().upper()
                    break
            if groupe_candidate:
                current_groupe = groupe_candidate

            # Chercher le CNE (colonne N° APOGEE)
            cne = None
            nom = None
            prenom = None

            cells = [c for c in row]
            for i, cell in enumerate(cells):
                cleaned = clean_cne(cell)
                if cleaned:
                    cne = cleaned
                    # NOM = cellule suivante, PRENOM = celle d'après
                    if i + 1 < len(cells) and cells[i + 1]:
                        nom = clean_name(cells[i + 1])
                    if i + 2 < len(cells) and cells[i + 2]:
                        prenom = clean_name(cells[i + 2])
                    break

            if cne and nom:
                result["students"].append({
                    "cne":        cne,
                    "nom":        nom,
                    "prenom":     prenom or "",
                    "groupe":     current_groupe or "",
                    "periode_num": current_periode,
                })

    return result


# ── Import principal ──────────────────────────────────────────────────────────

def import_all(base_dir: str):
    all_files = sorted(glob.glob(os.path.join(base_dir, "**", "*.xlsx"), recursive=True))

    if not all_files:
        print(f"❌ Aucun fichier .xlsx trouvé dans : {base_dir}")
        sys.exit(1)

    print(f"📂 {len(all_files)} fichiers trouvés\n")

    db = SessionLocal()
    dept_cache   = {}
    intern_cache = {}

    stats = {
        "files":      0,
        "depts":      0,
        "interns":    0,
        "rotations":  0,
        "skipped":    0,
        "errors":     [],
    }

    try:
        for filepath in all_files:
            folder = os.path.basename(os.path.dirname(filepath))
            fname  = os.path.basename(filepath)
            annee  = detect_year(folder)

            if annee is None:
                print(f"  ⚠️  Dossier non reconnu (année?) : {folder} — ignoré")
                stats["skipped"] += 1
                continue

            print(f"  📄 [{annee}EME] {fname[:55]}")

            try:
                parsed = parse_file(filepath, annee)
            except Exception as e:
                msg = f"Erreur parsing {fname}: {e}"
                stats["errors"].append(msg)
                print(f"     ❌ {msg}")
                continue

            if not parsed["service_name"]:
                print(f"     ⚠️  Service introuvable — ignoré")
                stats["skipped"] += 1
                continue

            # Département
            dept_id = get_or_create_department(db, parsed["service_name"], dept_cache)
            if dept_id not in [v for v in dept_cache.values()][:-1] if dept_cache else True:
                # Nouveau département créé
                pass

            # Construire un index des périodes : num → (debut, fin)
            periode_map = {}
            for p in parsed["periodes"]:
                if p["debut"] and p["fin"]:
                    periode_map[p["num"]] = (p["debut"], p["fin"])

            # Étudiants + rotations
            nb_interns  = 0
            nb_rotations = 0

            for s in parsed["students"]:
                if not s["cne"]:
                    continue

                # Intern
                intern_id = get_or_create_intern(
                    db, s["cne"], s["prenom"], s["nom"],
                    annee, s["groupe"], dept_id, intern_cache
                )

                if intern_id not in intern_cache.values():
                    nb_interns += 1

                # Rotation
                pnum = s["periode_num"]
                if pnum in periode_map:
                    debut, fin = periode_map[pnum]
                    inserted = upsert_rotation(db, intern_id, dept_id, pnum, debut, fin)
                    if inserted:
                        nb_rotations += 1
            
            db.flush()
            db.commit()
            stats["files"]     += 1
            stats["rotations"] += nb_rotations
            print(f"     ✅ {len(parsed['students'])} étudiants · {nb_rotations} rotations")

    except KeyboardInterrupt:
        print("\n⏹  Interrompu — données déjà commitées sont conservées.")
    except Exception as e:
        db.rollback()
        print(f"\n❌ Erreur fatale : {e}")
        raise
    finally:
        db.close()

    # Compte final depuis la DB
    db2 = SessionLocal()
    try:
        total_interns   = db2.query(Intern).filter(Intern.cne.isnot(None)).count()
        total_rotations = db2.query(Rotation).count()
        total_depts     = db2.query(Department).count()
    finally:
        db2.close()

    print(f"""
{'='*55}
✅ IMPORT TERMINÉ
{'='*55}
  Fichiers traités  : {stats['files']}
  Fichiers ignorés  : {stats['skipped']}
  Erreurs           : {len(stats['errors'])}

  État de la base :
  ├─ Départements   : {total_depts}
  ├─ Stagiaires     : {total_interns} (avec CNE)
  └─ Rotations      : {total_rotations}
""")

    if stats["errors"]:
        print("⚠️  Erreurs détectées :")
        for e in stats["errors"]:
            print(f"   • {e}")


# ── Point d'entrée ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Chemin par défaut : sous-dossier "stage médecine 3-4-5-6" dans le répertoire courant
    if len(sys.argv) > 1:
        base = sys.argv[1]
    else:
        # Chercher automatiquement
        candidates = glob.glob("**/3 EME ANNEE", recursive=True) + \
                     glob.glob("**/3EME*", recursive=True)
        if candidates:
            base = os.path.dirname(candidates[0])
        else:
            print("Usage : python import_stages.py /chemin/vers/dossier_stages")
            print("Le dossier doit contenir les sous-dossiers '3 EME ANNEE', '4 EME ANNEE', etc.")
            sys.exit(1)

    print(f"📂 Dossier source : {base}\n")
    import_all(base)