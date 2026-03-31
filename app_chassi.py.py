import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os # <--- O SEGREDO ESTÁ AQUI

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Dashboard Chassi", layout="wide")

st.title("🏎️ Matriz de Decisão: Protótipo do Chassi")
st.markdown("Selecione os materiais e ajuste os **pesos** no menu lateral para ver os resultados em tempo real.")

# --- 2. LEITURA DE DADOS (À PROVA DE FALHAS) ---
@st.cache_data
def carregar_dados():
    # Descobre a pasta EXATA onde este script está guardado
    pasta_atual = os.path.dirname(os.path.abspath(__file__))
    
    # Junta a pasta atual com o nome do Excel
    caminho_sem_til = os.path.join(pasta_atual, 'Matriz de Decisao Chassi- Prototipo_VFINAL.xlsx')
    caminho_com_til = os.path.join(pasta_atual, 'Matriz de Decisão Chassi- Prototipo_VFINAL.xlsx')
    
    try:
        return pd.read_excel(caminho_sem_til, sheet_name='Decision Matrix', skiprows=14, nrows=6)
    except:
        try:
            return pd.read_excel(caminho_com_til, sheet_name='Decision Matrix', skiprows=14, nrows=6)
        except Exception as e:
            st.error(f"Erro: O ficheiro Excel não foi encontrado dentro da pasta:\n{pasta_atual}")
            return None

df = carregar_dados()

if df is not None:
    # --- 3. MAPEAMENTO DE COLUNAS ---
    nomes_materiais = [
        'Fibra de Carbono', 'Fibra de Vidro', 'Aramida', 'Alumínio CHASSI', 
        'Aço 1020', 'Aço 4340', 'Aço 4130', 'Aço 1010', 'Titânio', 'Alumínio (Padrão)', 'Aço Inox'
    ]
    
    materiais_map = {}
    idx = 4
    for nome in nomes_materiais:
        if idx < len(df.columns):
            materiais_map[nome] = idx
        idx += 2

    # --- 4. BARRA LATERAL (CHECKBOXES DE MATERIAIS) ---
    st.sidebar.header("⚙️ 1. Materiais para Análise")
    st.sidebar.write("Marca ou desmarca para atualizar:")
    
    selecionados = []
    padroes = ['Fibra de Carbono', 'Alumínio CHASSI', 'Aço 1020']
    
    for mat in materiais_map.keys():
        if st.sidebar.checkbox(mat, value=(mat in padroes)):
            selecionados.append(mat)

    # --- 5. BARRA LATERAL (ROLL BARS / SLIDERS PARA PESOS) ---
    st.sidebar.markdown("---")
    st.sidebar.header("⚖️ 2. Pesos dos Critérios")
    st.sidebar.write("Desliza para alterar a importância:")
    
    pesos_dinamicos = {}
    for i, row in df.iterrows():
        criterio = str(row[df.columns[0]])
        peso_padrao = float(row[df.columns[1]]) if pd.notna(row[df.columns[1]]) else 10.0
        novo_peso = st.sidebar.slider(criterio, min_value=0.0, max_value=100.0, value=peso_padrao, step=1.0)
        pesos_dinamicos[criterio] = novo_peso

    # --- 6. EXIBIÇÃO DE GRÁFICOS E TABELAS ---
    if not selecionados:
        st.warning("👈 Por favor, seleciona pelo menos um material na barra lateral.")
    else:
        criterios = df.iloc[:, 0].astype(str).tolist()
        col1, col2 = st.columns(2)

        # GRÁFICO 1: RADAR DE DESEMPENHO (Dinâmico)
        with col1:
            st.subheader("🎯 Comparativo por Critério (Radar)")
            fig_radar = go.Figure()
            
            for mat in selecionados:
                col_idx = materiais_map[mat]
                notas_brutas = pd.to_numeric(df.iloc[:, col_idx], errors='coerce').fillna(0).tolist()
                
                # Multiplica a nota bruta pelo peso para o Radar se mexer!
                notas_ponderadas_radar = [n * pesos_dinamicos[c] for n, c in zip(notas_brutas, criterios)]
                notas_ponderadas_radar += [notas_ponderadas_radar[0]]
                criterios_fechados = criterios + [criterios[0]]
                
                fig_radar.add_trace(go.Scatterpolar(
                    r=notas_ponderadas_radar,
                    theta=criterios_fechados,
                    fill='toself',
                    name=mat,
                    opacity=0.7
                ))
            
            fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True)), showlegend=True, margin=dict(l=40, r=40, t=40, b=40))
            st.plotly_chart(fig_radar, use_container_width=True)

        # CÁLCULO DAS NOTAS PONDERADAS
        dados_barras = []
        df_tabela = pd.DataFrame({'Critério': criterios})
        linha_totais = {'Critério': '🏆 TOTAL PONDERADO'}

        for mat in selecionados:
            col_idx = materiais_map[mat]
            notas_brutas = pd.to_numeric(df.iloc[:, col_idx], errors='coerce').fillna(0).tolist()
            notas_ponderadas = [n * pesos_dinamicos[c] for n, c in zip(notas_brutas, criterios)]
            pontuacao_total = sum(notas_ponderadas)
            
            dados_barras.append({'Material': mat, 'Pontuação': pontuacao_total})
            df_tabela[f"{mat} (Nota Ponderada)"] = notas_ponderadas
            linha_totais[f"{mat} (Nota Ponderada)"] = pontuacao_total

        # GRÁFICO 2: PONTUAÇÃO TOTAL PONDERADA
        with col2:
            st.subheader("🏆 Pontuação Final Ponderada")
            df_barras = pd.DataFrame(dados_barras).sort_values(by='Pontuação', ascending=False)
            
            fig_bar = px.bar(
                df_barras, x='Material', y='Pontuação', text='Pontuação', color='Material',
                color_discrete_sequence=['#00FFFF', '#00CCCC', '#009999', '#006666', "#011F1F", "#6998C0"
                "#ABEBDE", "#0F5091", "#828BC3", "#333CD2", "#375050"][:len(selecionados)] 
                # Tons de Ciano!
            )
            fig_bar.update_traces(texttemplate='%{text:.1f}', textposition='outside')
            fig_bar.update_layout(yaxis_range=[0, max(df_barras['Pontuação']) * 1.2], showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)

        # TABELA: A MATRIZ DINÂMICA
        st.markdown("---")
        st.subheader("📋 Matriz de Decisão Dinâmica")
        df_tabela = pd.concat([df_tabela, pd.DataFrame([linha_totais])], ignore_index=True)
        df_fixo = df_tabela.set_index('Critério')
        st.dataframe(df_fixo.style.format("{:.1f}"), use_container_width=True)