import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Dashboard Chassi", layout="wide")

st.title("🏎️ Matriz de Decisão: Protótipo do Chassi")
st.markdown("Selecione os materiais e ajuste os **pesos** no menu lateral para ver os resultados em tempo real.")

# --- 2. LEITURA DE DADOS (CACHE) ---
@st.cache_data
def carregar_dados():
    # Modo Nuvem: Lê apenas o nome do ficheiro que está junto dele
    try:
        # ATENÇÃO: Mudamos nrows para 6. Já não precisamos da linha do "Total" do Excel, 
        # porque o nosso código agora vai calcular o total matematicamente!
        return pd.read_excel('Matriz de Decisao Chassi- Prototipo_VFINAL.xlsx', sheet_name='Decision Matrix', skiprows=14, nrows=6)
    except:
        try:
            return pd.read_excel('Matriz de Decisão Chassi- Prototipo_VFINAL.xlsx', sheet_name='Decision Matrix', skiprows=14, nrows=6)
        except Exception as e:
            st.error("Erro: O ficheiro Excel não foi encontrado junto ao script. Confirme se o nome está idêntico.")
            return None

df = carregar_dados()

if df is not None:
    # --- 3. MAPEAMENTO INTELIGENTE DE COLUNAS ---
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
    st.sidebar.write("Desliza para alterar a importância de cada critério:")
    
    pesos_dinamicos = {}
    for i, row in df.iterrows():
        criterio = str(row[df.columns[0]])
        peso_padrao = float(row[df.columns[1]]) if pd.notna(row[df.columns[1]]) else 10.0
        
        # Cria a "roll bar" (slider) para o critério
        novo_peso = st.sidebar.slider(criterio, min_value=0.0, max_value=100.0, value=peso_padrao, step=1.0)
        pesos_dinamicos[criterio] = novo_peso

    # --- 6. EXIBIÇÃO DE GRÁFICOS E TABELAS ---
    if not selecionados:
        st.warning("👈 Por favor, seleciona pelo menos um material na barra lateral.")
    else:
        criterios = df.iloc[:, 0].astype(str).tolist()

        col1, col2 = st.columns(2)

        # GRÁFICO 1: RADAR DE DESEMPENHO (Usa as notas brutas de 1 a 5)
        with col1:
            st.subheader("🎯 Comparativo por Critério (Radar)")
            fig_radar = go.Figure()
            
            for mat in selecionados:
                col_idx = materiais_map[mat]
                notas = pd.to_numeric(df.iloc[:, col_idx], errors='coerce').fillna(0).tolist()
                
                # Fechar o polígono do radar
                notas += [notas[0]]
                criterios_fechados = criterios + [criterios[0]]
                
                fig_radar.add_trace(go.Scatterpolar(
                    r=notas,
                    theta=criterios_fechados,
                    fill='toself',
                    name=mat,
                    opacity=0.7
                ))
            
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 5.5])),
                showlegend=True,
                margin=dict(l=40, r=40, t=40, b=40)
            )
            st.plotly_chart(fig_radar, use_container_width=True)


        # --- CÁLCULO DAS NOTAS PONDERADAS EM TEMPO REAL ---
        dados_barras = []
        df_tabela = pd.DataFrame({'Critério': criterios})
        linha_totais = {'Critério': '🏆 TOTAL PONDERADO'}

        for mat in selecionados:
            col_idx = materiais_map[mat]
            notas_brutas = pd.to_numeric(df.iloc[:, col_idx], errors='coerce').fillna(0).tolist()
            
            # Matemática: Multiplica a nota da planilha pelo peso do Slider!
            notas_ponderadas = [n * pesos_dinamicos[c] for n, c in zip(notas_brutas, criterios)]
            pontuacao_total = sum(notas_ponderadas)
            
            # Guarda os resultados para o Gráfico de Barras e para a Tabela
            dados_barras.append({'Material': mat, 'Pontuação': pontuacao_total})
            df_tabela[f"{mat} (Nota Ponderada)"] = notas_ponderadas
            linha_totais[f"{mat} (Nota Ponderada)"] = pontuacao_total


        # GRÁFICO 2: PONTUAÇÃO TOTAL PONDERADA (Atualizado com os sliders)
        with col2:
            st.subheader("🏆 Pontuação Final Ponderada")
            
            df_barras = pd.DataFrame(dados_barras).sort_values(by='Pontuação', ascending=False)
            
            fig_bar = px.bar(
                df_barras, 
                x='Material', 
                y='Pontuação', 
                text='Pontuação',
                color='Material',
                color_discrete_sequence=px.colors.qualitative.Plotly
            )
            fig_bar.update_traces(texttemplate='%{text:.1f}', textposition='outside')
            fig_bar.update_layout(yaxis_range=[0, max(df_barras['Pontuação']) * 1.2], showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)


        # TABELA: A MATRIZ DINÂMICA (Apenas Ponderados)
        st.markdown("---")
        st.subheader("📋 Matriz de Decisão Dinâmica (Apenas Notas Ponderadas)")
        
        # Junta a linha do Somatório Total ao fim da tabela
        df_tabela = pd.concat([df_tabela, pd.DataFrame([linha_totais])], ignore_index=True)
        
        # Define o 'Critério' como índice para ficar congelado no ecrã (Scroll Freeze)
        df_fixo = df_tabela.set_index('Critério')
        
        # Mostra a tabela (o '.style.format' deixa os números bonitos com apenas 1 casa decimal)
        st.dataframe(df_fixo.style.format("{:.1f}"), use_container_width=True)