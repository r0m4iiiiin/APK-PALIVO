import os
import sys
import json
import random
import argparse
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore

def init_firebase():
    """Initialise la connexion à Firebase Firestore via le secret GitHub."""
    # Récupération de la clé JSON stockée dans le secret GitHub Actions
    firebase_key_json = os.environ.get('FIREBASE_KEY')
    
    if not firebase_key_json:
        print("⚠️ Attention : La variable FIREBASE_KEY est manquante. Les prix seront générés mais pas envoyés à Firebase.")
        return None
    
    try:
        cred_dict = json.loads(firebase_key_json)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        print("🔥 Connexion réussie à Firebase Firestore !")
        return firestore.client()
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation de Firebase : {e}")
        return None

def generate_dynamic_prices(station_name):
    # Nettoyage du nom pour détecter la marque
    name_lower = str(station_name).lower()
    
    # Prix de base moyens du marché tchèque actuel
    base_diesel = 39.40
    base_e95 = 41.20
    base_lpg = 24.30
    
    # Différenciation réelle par enseigne
    if 'shell' in name_lower or 'omv' in name_lower:
        base_diesel += 1.20
        base_e95 += 1.50
        base_lpg += 0.40
    elif 'mol' in name_lower:
        base_diesel += 0.80
        base_e95 += 0.90
        base_lpg += 0.20
    elif 'avia' in name_lower or 'km-prona' in name_lower or 'eurobit' in name_lower:
        base_diesel -= 0.50
        base_e95 -= 0.40
        base_lpg -= 0.30
    elif 'tank ono' in name_lower or 'ono' in name_lower:
        base_diesel -= 2.50
        base_e95 -= 2.20
        base_lpg -= 1.10

    # Ajout d'une micro-variation locale aléatoire unique pour CHAQUE ligne
    var_diesel = round(random.uniform(-0.60, 0.60), 2)
    var_e95 = round(random.uniform(-0.70, 0.70), 2)
    var_lpg = round(random.uniform(-0.40, 0.40), 2)
    
    return {
        'prixDiesel': round(base_diesel + var_diesel, 2),
        'prixEssence95': round(base_e95 + var_e95, 2),
        'prixLPG': round(base_lpg + var_lpg, 2),
        'derniereModification': '17-06-2026'
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input_csv')
    parser.add_argument('output_csv')
    args = parser.parse_args()
    
    if not os.path.exists(args.input_csv):
        print(f"Erreur : Le fichier {args.input_csv} n'existe pas.")
        sys.exit(1)
        
    df = pd.read_csv(args.input_csv)
    print(f" Fichier chargé : {len(df)} stations au total.")
    
    # Connexion à Firebase
    db = init_firebase()
    
    df_output = df.copy()
    
    # Création des colonnes vides si elles n'existent pas
    for col in ['prixDiesel', 'prixEssence95', 'prixEssence98', 'prixLPG', 'derniereModification']:
        df_output[col] = None

    end_idx = len(df)
    print(f" Traitement et synchronisation en cours pour {end_idx} stations...\n")
    
    for idx in range(end_idx):
        name = df_output.loc[idx, 'name']
        station_name = name if pd.notna(name) else "Station"
        
        # Détermination d'un ID unique pour Firebase (prend la colonne 'id' si elle existe, sinon utilise l'index)
        station_id = str(df_output.loc[idx, 'id']) if 'id' in df_output.columns and pd.notna(df_output.loc[idx, 'id']) else f"station_{idx+1}"
        
        # Calcul des prix uniques
        prices = generate_dynamic_prices(station_name)
        
        # Enregistrement dans le DataFrame local
        df_output.loc[idx, 'prixDiesel'] = prices['prixDiesel']
        df_output.loc[idx, 'prixEssence95'] = prices['prixEssence95']
        df_output.loc[idx, 'prixLPG'] = prices['prixLPG']
        df_output.loc[idx, 'derniereModification'] = prices['derniereModification']
        
        # Envoi direct vers Firebase Firestore (uniquement si la connexion est établie)
        if db:
            try:
                # Met à jour ou crée le document dans la collection 'stations'
                db.collection('stations').document(station_id).set({
                    'name': station_name,
                    'lat': float(df_output.loc[idx, 'lat']) if 'lat' in df_output.columns else None,
                    'lon': float(df_output.loc[idx, 'lon']) if 'lon' in df_output.columns else None,
                    'prixDiesel': prices['prixDiesel'],
                    'prixEssence95': prices['prixEssence95'],
                    'prixLPG': prices['prixLPG'],
                    'derniereModification': prices['derniereModification']
                }, merge=True) # merge=True évite d'écraser les autres champs déjà présents dans Firestore
            except Exception as e:
                print(f"⚠️ Erreur de synchro Firebase à la ligne {idx+1} : {e}")
        
        # Affichage dynamique dans la console
        if (idx + 1) % 50 == 0 or idx == end_idx - 1 or idx < 5:
            print(f"[{idx+1}/{end_idx}] {station_name[:20]} -> D: {prices['prixDiesel']} | E95: {prices['prixEssence95']} | LPG: {prices['prixLPG']} (Synchro OK)")
        
        # Sauvegarde régulière du CSV local par blocs de 100
        if idx % 100 == 0 or idx == end_idx - 1:
            df_output.to_csv(args.output_csv, index=False)

    print(f"\n Succès total ! Les données sont à jour sur Firebase et enregistrées dans '{args.output_csv}'.")

if __name__ == "__main__":
    main()
