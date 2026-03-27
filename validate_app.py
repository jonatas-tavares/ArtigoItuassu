import streamlit as st
import pandas as pd
import glob
import os
from urllib.parse import quote

st.set_page_config(layout="wide", page_title="Validador Social Media Pro")

# --- ESTILO ---
st.markdown("""
    <style>
    .stButton button { width: 100%; padding: 5px; }
    .status-badge { 
        padding: 8px 15px; 
        border-radius: 8px; 
        font-size: 1em; 
        font-weight: bold; 
        display: inline-block;
        margin-top: 5px;
        text-transform: uppercase;
    }
    .validado { background-color: #28a745 !important; color: white !important; border: 2px solid #1e7e34; }
    .erro { background-color: #dc3545 !important; color: white !important; border: 2px solid #bd2130; }
    .pendente { background-color: #ffc107 !important; color: #212529 !important; border: 2px solid #e0a800; }
    
    .handle-text {
        color: #007bff;
        font-family: 'Courier New', Courier, monospace;
        font-weight: bold;
        font-size: 1.2em;
        text-decoration: none;
    }
    .label-text {
        color: #495057;
        font-weight: bold;
        margin-right: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- CARREGAMENTO DE DADOS ---
csv_files = glob.glob("data/*.csv")
if not csv_files:
    st.error("Nenhum arquivo CSV encontrado na pasta data/")
    st.stop()

csv_path = st.sidebar.selectbox("Escolha o arquivo CSV", csv_files)

def get_fresh_data(path):
    temp_df = pd.read_csv(path)
    dirty = False
    if 'ig_status' not in temp_df.columns: 
        temp_df['ig_status'] = 'Pendente'
        dirty = True
    if 'fb_status' not in temp_df.columns: 
        temp_df['fb_status'] = 'Pendente'
        dirty = True
    if 'observacoes' not in temp_df.columns:
        temp_df['observacoes'] = ''
        dirty = True
        
    temp_df['ig_handle'] = temp_df['ig_handle'].astype(str).replace('nan', '')
    temp_df['fb_handle'] = temp_df['fb_handle'].astype(str).replace('nan', '')
    temp_df['observacoes'] = temp_df['observacoes'].astype(str).replace('nan', '')
    
    if dirty:
        temp_df.to_csv(path, index=False)
    return temp_df

df = get_fresh_data(csv_path)

# --- FILTROS ---
st.sidebar.title("Filtros")
f_opt = st.sidebar.radio("Mostrar:", ["Todos", "Pendentes (Qualquer)", "Pendentes IG", "Pendentes FB"])

if f_opt == "Pendentes (Qualquer)":
    v_indices = df[(df['ig_status'] == 'Pendente') | (df['fb_status'] == 'Pendente')].index.tolist()
elif f_opt == "Pendentes IG":
    v_indices = df[df['ig_status'] == 'Pendente'].index.tolist()
elif f_opt == "Pendentes FB":
    v_indices = df[df['fb_status'] == 'Pendente'].index.tolist()
else:
    v_indices = df.index.tolist()

if not v_indices:
    st.success("Tudo validado com este filtro!")
    if st.sidebar.button("Ver Todos"): st.rerun()
    st.stop()

# Navegação
if 'current_id' not in st.session_state or st.session_state.current_id not in v_indices:
    st.session_state.current_id = v_indices[0]

def move_next():
    c_pos = v_indices.index(st.session_state.current_id)
    if c_pos < len(v_indices) - 1:
        st.session_state.current_id = v_indices[c_pos + 1]

def move_prev():
    c_pos = v_indices.index(st.session_state.current_id)
    if c_pos > 0:
        st.session_state.current_id = v_indices[c_pos - 1]

# Sidebar Navegação
st.sidebar.divider()
try:
    c_pos_disp = v_indices.index(st.session_state.current_id) + 1
except:
    st.session_state.current_id = v_indices[0]
    c_pos_disp = 1

st.sidebar.subheader(f"Candidato {c_pos_disp} de {len(v_indices)}")
c_nav1, c_nav2 = st.sidebar.columns(2)
c_nav1.button("⬅️ Anterior", on_click=move_prev)
c_nav2.button("Próximo ➡️", on_click=move_next)

# --- CORPO ---
a_idx = st.session_state.current_id
row = df.loc[a_idx]

# Destaque de conclusão no nome
is_done = row['ig_status'] == 'Validado' and row['fb_status'] == 'Validado'
done_mark = " ✅" if is_done else ""
st.title(f"👤 {row['nm_candidato']}{done_mark}")
st.subheader(f"{row['uf']} | Urna: {row['display_name']}")

# Edição de Handles
c_ed1, c_ed2 = st.columns(2)
new_ig = c_ed1.text_input("Instagram Handle", value=row['ig_handle'], key=f"ig_{a_idx}")
new_fb = c_ed2.text_input("Facebook Handle", value=row['fb_handle'], key=f"fb_{a_idx}")

# Campo de Observações
new_obs = st.text_area("🗒️ Observações", value=row['observacoes'], key=f"obs_{a_idx}", placeholder="Digite notas ou avisos aqui...")

# Salvar mudanças se houver edição
if new_ig != row['ig_handle'] or new_fb != row['fb_handle'] or new_obs != row['observacoes']:
    df.at[a_idx, 'ig_handle'] = new_ig
    df.at[a_idx, 'fb_handle'] = new_fb
    df.at[a_idx, 'observacoes'] = new_obs
    df.to_csv(csv_path, index=False)

def clean(h): return str(h).strip().replace('@', '').split(' ')[0].split('(')[0]
ig_url = f"https://www.instagram.com/{clean(new_ig)}/" if clean(new_ig) else None
fb_url = f"https://www.facebook.com/{clean(new_fb)}/" if clean(new_fb) else None
g_search = f"https://www.google.com/search?q={quote(row['nm_candidato'] + ' ' + row['uf'])}"

st.divider()

if st.button("🚀 ABRIR TUDO (Google + Redes)"):
    js = "".join([f"window.open('{u}', '_blank');" for u in [g_search, ig_url, fb_url] if u])
    st.components.v1.html(f"<script>{js}</script>", height=0)

st.divider()

# --- ÁREA DE VALIDAÇÃO ---
@st.fragment
def render_validation_area(idx, ig_u, fb_u, csv_p):
    current_df = pd.read_csv(csv_p)
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📸 Instagram")
        if ig_u:
            st.markdown(f"<span class='label-text'>Link:</span> <a href='{ig_u}' target='_blank' class='handle-text'>@{clean(current_df.at[idx, 'ig_handle'])}</a>", unsafe_allow_html=True)
            cv1, cv2, cv3 = st.columns(3)
            if cv1.button("✅ OK", key=f"f_ig_ok_{idx}"):
                current_df.at[idx, 'ig_status'] = 'Validado'
                current_df.to_csv(csv_p, index=False)
                if current_df.at[idx, 'fb_status'] == 'Validado': 
                    move_next()
                    st.rerun()
                else:
                    st.rerun()
            if cv2.button("❌ Erro", key=f"f_ig_er_{idx}"):
                current_df.at[idx, 'ig_status'] = 'Erro'
                current_df.to_csv(csv_p, index=False)
                st.rerun()
            if cv3.button("⏳ Pend.", key=f"f_ig_pe_{idx}"):
                current_df.at[idx, 'ig_status'] = 'Pendente'
                current_df.to_csv(csv_p, index=False)
                st.rerun()
            s = current_df.at[idx, 'ig_status']
            st.markdown(f"<span class='status-badge {s.lower()}'>{s}</span>", unsafe_allow_html=True)
        else:
            st.warning("Sem Instagram")

    with col2:
        st.markdown("### 👥 Facebook")
        if fb_u:
            st.markdown(f"<span class='label-text'>Link:</span> <a href='{fb_u}' target='_blank' class='handle-text'>fb.com/{clean(current_df.at[idx, 'fb_handle'])}</a>", unsafe_allow_html=True)
            cv1, cv2, cv3 = st.columns(3)
            if cv1.button("✅ OK", key=f"f_fb_ok_{idx}"):
                current_df.at[idx, 'fb_status'] = 'Validado'
                current_df.to_csv(csv_p, index=False)
                if current_df.at[idx, 'ig_status'] == 'Validado':
                    move_next()
                    st.rerun()
                else:
                    st.rerun()
            if cv2.button("❌ Erro", key=f"f_fb_er_{idx}"):
                current_df.at[idx, 'fb_status'] = 'Erro'
                current_df.to_csv(csv_p, index=False)
                st.rerun()
            if cv3.button("⏳ Pend.", key=f"f_fb_pe_{idx}"):
                current_df.at[idx, 'fb_status'] = 'Pendente'
                current_df.to_csv(csv_p, index=False)
                st.rerun()
            s = current_df.at[idx, 'fb_status']
            st.markdown(f"<span class='status-badge {s.lower()}'>{s}</span>", unsafe_allow_html=True)
        else:
            st.warning("Sem Facebook")

render_validation_area(a_idx, ig_url, fb_url, csv_path)

st.divider()
st.markdown(f"🔍 **Referência:** [Pesquisar no Google]({g_search})")

# Progresso (Sidebar)
st.sidebar.divider()
ig_val = len(df[df['ig_status'] != 'Pendente'])
fb_val = len(df[df['fb_status'] != 'Pendente'])
st.sidebar.write(f"📊 IG: {ig_val}/{len(df)} | FB: {fb_val}/{len(df)}")
st.sidebar.progress(ig_val/len(df) if len(df) > 0 else 0)
