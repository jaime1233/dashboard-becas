import streamlit as st
import pandas as pd
import os

# Configuración de página
st.set_page_config(page_title="Balance Nacional de Becas", layout="wide")

# Ruta del archivo Parquet
ARCHIVO_DATOS = "para_cat_escuelas_enero2026.parquet"

@st.cache_data
def cargar_datos_automatico():
    if os.path.exists(ARCHIVO_DATOS):
        df = pd.read_parquet(ARCHIVO_DATOS)
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype('category')
        return df
    return None

st.title("📊 Dashboard Nacional de Escuelas")

with st.spinner('Cargando base de datos...'):
    df = cargar_datos_automatico()

if df is not None:
    # --- DICCIONARIOS DE TRADUCCIÓN ---
    dic_estados = {
        1:'AGUASCALIENTES', 2:'BAJA CALIFORNIA', 3:'BAJA CALIFORNIA SUR', 4:'CAMPECHE',
        5:'COAHUILA', 6:'COLIMA', 7:'CHIAPAS', 8:'CHIHUAHUA', 9:'CIUDAD DE MÉXICO',
        10:'DURANGO', 11:'GUANAJUATO', 12:'GUERRERO', 13:'HIDALGO', 14:'JALISCO',
        15:'MÉXICO', 16:'MICHOACÁN', 17:'MORELOS', 18:'NAYARIT', 19:'NUEVO LEÓN',
        20:'OAXACA', 21:'PUEBLA', 22:'QUERÉTARO', 23:'QUINTANA ROO', 24:'SAN LUIS POTOSÍ',
        25:'SINALOA', 26:'SONORA', 27:'TABASCO', 28:'TAMAULIPAS', 29:'TLAXCALA',
        30:'VERACRUZ', 31:'YUCATÁN', 32:'ZACATECAS'
    }

    dic_clasif = {
        1: 'Prioritaria',
        2: 'Susceptible',
        3: 'No Susceptible'
    }

    # Mapeo de IDs a Texto
    df['ESTADO_TEXTO'] = df['ID_EDO'].map(dic_estados)
    df['CLASIF_TEXTO'] = df['GPO_INDV7'].map(dic_clasif)

    st.success(f"Base de datos cargada automáticamente: {len(df):,} registros.")
    
    df = df[df['CATREF2601'] > 0].copy()


    # --- FILTROS LATERALES ---
    st.sidebar.header("Filtros del Balance")
    
    lista_programas = sorted(df['PROGRAMA'].unique().tolist())
    prog_sel = st.sidebar.multiselect("Selecciona Programa:", options=lista_programas, default=lista_programas)
    
    lista_clasif = sorted(df['CLASIF_TEXTO'].dropna().unique().tolist())
    clas_sel = st.sidebar.multiselect("Selecciona Clasificación:", options=lista_clasif, default=lista_clasif)

    # Aplicar filtros
    df_f = df[(df['PROGRAMA'].isin(prog_sel)) & (df['CLASIF_TEXTO'].isin(clas_sel))]

    # --- CÁLCULOS DEL BALANCE ---
    balance = df_f.groupby('ESTADO_TEXTO').agg(
        Total_Escuelas=('CLAVECCT', 'count'),
        Total_Matricula=('MATR24_25', 'sum'),
        Total_Becarios=('BE5_231225', 'sum'),
        Escuelas_con_Becas=('BE5_231225', lambda x: (x > 0).sum())
    ).reset_index()
    
    balance = balance.rename(columns={'ESTADO_TEXTO': 'ESTADO'})

    # Fila de Total Nacional
    totales_general = pd.DataFrame({
        'ESTADO': ['⭐ TOTAL NACIONAL'], 
        'Total_Escuelas': [balance['Total_Escuelas'].sum()],
        'Total_Matricula': [balance['Total_Matricula'].sum()],
        'Total_Becarios': [balance['Total_Becarios'].sum()],
        'Escuelas_con_Becas': [balance['Escuelas_con_Becas'].sum()]
    })

    # Calcular coberturas
    for d in [balance, totales_general]:
        d['%_Cobertura_Matricula'] = (d['Total_Becarios'] / d['Total_Matricula'] * 100).fillna(0)
        d['%_Cobertura_Escuelas'] = (d['Escuelas_con_Becas'] / d['Total_Escuelas'] * 100).fillna(0)

    # --- VISUALIZACIÓN ---


    # 2. TABLA FIJA DE TOTALES (No se mueve al hacer scroll)
    st.subheader("📋 Resumen Nacional (Fijo)")
    st.table(
        totales_general.style.format({
            'Total_Matricula': '{:,.0f}', 'Total_Becarios': '{:,.0f}',
            'Total_Escuelas': '{:,.0f}', 'Escuelas_con_Becas': '{:,.0f}',
            '%_Cobertura_Matricula': '{:.2f}%', '%_Cobertura_Escuelas': '{:.2f}%'
        })
    )

    # 3. TABLA CON DESGLOSE POR ESTADO (Con scroll y búsqueda)
    st.subheader("📍 Detalle por Estado")
    st.dataframe(
        balance.style.format({
            'Total_Matricula': '{:,.0f}', 'Total_Becarios': '{:,.0f}',
            'Total_Escuelas': '{:,.0f}', 'Escuelas_con_Becas': '{:,.0f}',
            '%_Cobertura_Matricula': '{:.2f}%', '%_Cobertura_Escuelas': '{:.2f}%'
        }), 
        use_container_width=True,
        height=400 
    )

    # 4. GRÁFICA
    st.subheader("📈 Comparativo: Matrícula vs Becarios")
    st.bar_chart(balance.set_index('ESTADO')[['Total_Matricula', 'Total_Becarios']])

# --- BOTÓN DE DESCARGA ---
    st.divider()
    st.subheader("📥 Exportar Resultados")
    
    # IMPORTANTE: Creamos df_final uniendo el total con el desglose
    df_final = pd.concat([totales_general, balance], ignore_index=True)
    
    # Convertimos a CSV para máxima compatibilidad con Excel
    # Usamos utf-8-sig para que Excel reconozca acentos y la Ñ
    csv_data = df_final.to_csv(index=False).encode('utf-8-sig') 
    
    st.download_button(
        label="💾 Descargar Balance Nacional en Excel (CSV)",
        data=csv_data,
        file_name='balance_nacional_becas_2026.csv',
        mime='text/csv',
        use_container_width=True
    )

else:
    st.error(f"No encontré el archivo '{ARCHIVO_DATOS}'.")
    st.info("Asegúrate de que el archivo .parquet esté en la ruta: r:/trabajo_2026/dashboard_escuelas/")

    