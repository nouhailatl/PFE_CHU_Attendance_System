# Frontend Python

Petit serveur Flask pour servir le dashboard et le scanner, puis proxyfier les appels API vers le backend FastAPI.

## Lancement manuel

```bat
cd Frontend
pip install -r requirements.txt
python app.py
```

URL par défaut: http://127.0.0.1:5000

Variables utiles:

- `BACKEND_URL`: URL du backend FastAPI, par défaut `http://127.0.0.1:8000`
- `FRONTEND_PORT`: port Flask, par défaut `5000`
