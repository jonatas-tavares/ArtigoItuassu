import csv
import requests
import time
import re
import unicodedata

def normalize(text):
    if not text:
        return ""
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return text.strip().lower()

def get_camara_deputados():
    # Legislatura 56 = 2019-2023 (elected in 2018)
    url = "https://dadosabertos.camara.leg.br/api/v2/deputados?idLegislatura=56&itens=1000"
    headers = {'accept': 'application/json'}
    try:
        print("Fetching all deputies from Camara API (Legislatura 56)...")
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code == 200:
            return response.json().get('dados', [])
    except Exception as e:
        print(f"Error fetching from Camara: {e}")
    return []

def get_deputy_details(dep_id):
    url = f"https://dadosabertos.camara.leg.br/api/v2/deputados/{dep_id}"
    headers = {'accept': 'application/json'}
    try:
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code == 200:
            return response.json().get('dados', {})
    except Exception as e:
        print(f"Error fetching details for deputy {dep_id}: {e}")
    return {}

def get_tse_candidates_list(uf):
    url = f"https://divulgacandcontas.tse.jus.br/divulga/rest/v1/candidatura/listar/2018/{uf}/2022802018/6/candidatos"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            return response.json().get('candidatos', [])
    except Exception as e:
        print(f"Error fetching list for {uf}: {e}")
    return []

def get_tse_candidate_details(uf, cand_id):
    url = f"https://divulgacandcontas.tse.jus.br/divulga/rest/v1/candidatura/buscar/2018/{uf}/2022802018/candidato/{cand_id}"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching details for {cand_id}: {e}")
    return {}

def extract_handles(urls):
    ig = ""
    fb = ""
    if not urls:
        return ig, fb
    
    for url in urls:
        if not url: continue
        url = url.lower()
        if 'instagram.com/' in url:
            match = re.search(r'instagram\.com/([^/?#\s]+)', url)
            if match:
                ig = match.group(1).rstrip('/')
        elif 'facebook.com/' in url:
            match = re.search(r'facebook\.com/([^/?#\s]+)', url)
            if match:
                fb = match.group(1).rstrip('/')
    return ig, fb

def main():
    input_file = 'elected_deputado_federal_2018_names_part3.csv'
    output_file = 'elected_deputado_federal_2018_names_part3_updated.csv'
    
    with open(input_file, mode='r', encoding='utf-8-sig') as f:
        reader = list(csv.DictReader(f))
    
    # --- PHASE 1: CAMARA API ---
    camara_list = get_camara_deputados()
    camara_map = {normalize(d['nome']): d['id'] for d in camara_list}
    # Some matching by UF to be sure
    camara_map_uf = { (normalize(d['nome']), d['siglaUf']): d['id'] for d in camara_list }

    # --- PHASE 2: TSE API PREP ---
    ufs = sorted(list(set(row['uf'] for row in reader)))
    tse_uf_maps = {} # (uf, normalized_name) -> id
    
    updated_rows = []
    for row in reader:
        nm_norm = normalize(row['nm_candidato'])
        disp_norm = normalize(row['display_name'])
        uf = row['uf']
        
        # Priority 1: Camara (usually more updated for elected ones)
        if not row['ig_handle'] or not row['fb_handle']:
            dep_id = camara_map_uf.get((nm_norm, uf)) or camara_map_uf.get((disp_norm, uf)) or camara_map.get(nm_norm) or camara_map.get(disp_norm)
            if dep_id:
                print(f"Found {row['nm_candidato']} in Camara API ({dep_id})")
                details = get_deputy_details(dep_id)
                rede_social = details.get('redeSocial', [])
                ig, fb = extract_handles(rede_social)
                if ig and not row['ig_handle']:
                    row['ig_handle'] = ig
                    print(f"  Camara IG: {ig}")
                if fb and not row['fb_handle']:
                    row['fb_handle'] = fb
                    print(f"  Camara FB: {fb}")

        # Priority 2: TSE (if still missing)
        if not row['ig_handle'] or not row['fb_handle']:
            if uf not in tse_uf_maps:
                print(f"Fetching TSE candidates for {uf}...")
                cands = get_tse_candidates_list(uf)
                tse_uf_maps[uf] = {normalize(c['nomeCompleto']): c['id'] for c in cands}
                tse_uf_maps[uf].update({normalize(c['nomeUrna']): c['id'] for c in cands})
                time.sleep(1)
            
            cand_id = tse_uf_maps[uf].get(nm_norm) or tse_uf_maps[uf].get(disp_norm)
            if cand_id:
                print(f"Fetching TSE details for {row['nm_candidato']} ({cand_id})...")
                details = get_tse_candidate_details(uf, cand_id)
                ig, fb = extract_handles(details.get('sites', []))
                if ig and not row['ig_handle']:
                    row['ig_handle'] = ig
                if fb and not row['fb_handle']:
                    row['fb_handle'] = fb
                time.sleep(0.5)

        updated_rows.append(row)
    
    with open(output_file, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=reader[0].keys())
        writer.writeheader()
        writer.writerows(updated_rows)

if __name__ == "__main__":
    main()
