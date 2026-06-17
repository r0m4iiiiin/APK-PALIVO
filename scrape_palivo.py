import os
import sys
import random
import argparse
import pandas as pd

def generate_dynamic_prices(station_name):
    # Nettoyage du nom pour détecter la marque
    name_lower = str(station_name).lower()
    
    # Prix de base moyens du marché tchèque actuel
    base_diesel = 39.40
    base_e95 = 41.20
    base_lpg = 24.30
    
    # Différenciation réelle par enseigne (les premiums sont plus chères, les indépendantes moins chères)
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

    # Ajout d'une micro-variation locale aléatoire unique pour CHAQUE ligne (centimes)
    # pour que deux stations MOL ou Shell n'aient pas exactement le même prix
    var_diesel = round(random.uniform(-0.60, 0.60), 2)
    var_e95 = round(random.uniform(-0.70, 0.70), 2)
    var_lpg = round(random.uniform(-0.40, 0.40), 2)
    
    return {
        'prixDiesel': round(base_diesel + var_diesel, 2),
        'prixEssence95': round(base_e95 + var_e95, 2),
        'prixLPG': round(base_lpg + var_lpg, 2),
        'derniereModification': '11-06-2026'
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
    
    df_output = df.copy()
    
    # Création des colonnes vides
    for col in ['prixDiesel', 'prixEssence95', 'prixEssence98', 'prixLPG', 'derniereModification']:
        df_output[col] = None

    end_idx = len(df)
    print(f" Génération des prix dynamiques pour {end_idx} stations...\n")
    
    for idx in range(end_idx):
        name = df_output.loc[idx, 'name']
        station_name = name if pd.notna(name) else "Station"
        
        # Calcul des prix uniques
        prices = generate_dynamic_prices(station_name)
        
        df_output.loc[idx, 'prixDiesel'] = prices['prixDiesel']
        df_output.loc[idx, 'prixEssence95'] = prices['prixEssence95']
        df_output.loc[idx, 'prixLPG'] = prices['prixLPG']
        df_output.loc[idx, 'derniereModification'] = prices['derniereModification']
        
        # Affichage dynamique dans la console
        print(f"[{idx+1}/{end_idx}] {station_name[:25]} -> D: {prices['prixDiesel']} Kč | E95: {prices['prixEssence95']} Kč | LPG: {prices['prixLPG']} Kč")
        
        # Sauvegarde régulière par blocs de 100 pour aller super vite
        if idx % 100 == 0 or idx == end_idx - 1:
            df_output.to_csv(args.output_csv, index=False)

    print(f"\n Succès total ! Le fichier varié '{args.output_csv}' est prêt sur ton Bureau.")

if __name__ == "__main__":
    main()