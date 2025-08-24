import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# ============================
# 📊 Configuración inicial
# ============================
st.set_page_config(page_title="Ranking Campeonato Sniper Elite", layout="wide")
st.title("📊 Campeonato Sniper Elite Resistencia – Consolidado por Jugador")

archivo = "Estadiscticas Campeonato interno Sniper Elite 6_ver2.xlsx"

# ============================
# 📥 Cargar y limpiar datos (solo primeras 6 hojas)
# ============================
all_sheets = pd.read_excel(archivo, sheet_name=None, skiprows=4)
sheets_to_use = list(all_sheets.keys())[:6]

df_list = []
for name in sheets_to_use:
    tmp = all_sheets[name].copy()
    tmp["hoja"] = name  # por trazabilidad
    df_list.append(tmp)

df = pd.concat(df_list, ignore_index=True)

# Normalizar nombres de columnas
df.columns = (
    df.columns.str.strip()
    .str.lower()
    .str.replace(" ", "_")
    .str.replace("á", "a")
    .str.replace("é", "e")
    .str.replace("í", "i")
    .str.replace("ó", "o")
    .str.replace("ú", "u")
)

# Mostrar columnas para depuración
st.write("✅ Columnas detectadas después de normalización:", df.columns.tolist())

# Convertir columnas numéricas
cols_num = ["bajas", "muertes", "rendimiento", "ratio"]
for col in cols_num:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    else:
        st.warning(f"⚠️ La columna '{col}' no está en el archivo. Columnas actuales: {df.columns.tolist()}")

# ============================
# 📌 KPIs principales
# ============================
st.subheader("📌 KPIs del Campeonato")

if "rendimiento" in df.columns:
    rendimiento_total = df.groupby("jugador")["rendimiento"].sum().reset_index()
    top_jugador = rendimiento_total.loc[rendimiento_total["rendimiento"].idxmax()]

    mejor_ratio = df.groupby("jugador")["ratio"].mean().reset_index()
    top_ratio = mejor_ratio.loc[mejor_ratio["ratio"].idxmax()]

    col1, col2, col3 = st.columns(3)
    col1.metric("🏆 Jugador con mayor rendimiento", top_jugador["jugador"], f"{top_jugador['rendimiento']:.0f}")
    col2.metric("🔥 Mejor Ratio", top_ratio["jugador"], f"{top_ratio['ratio']:.2f}")
    col3.metric("📊 Promedio Global Rendimiento", f"{df['rendimiento'].mean():.2f}")
else:
    st.warning("⚠️ No se encontró la columna 'rendimiento' en el archivo.")

# ============================
# 📂 Tabs de navegación
# ============================
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["🏆 Ranking", "📋 Tablas Detalladas", "⚖️ Equipos", "🌍 Por Fecha", "📈 Visualizaciones"]
)

# ---------------- TAB 1: Ranking ----------------
with tab1:
    st.subheader("🏆 Ranking General de Jugadores")
    ranking = df.groupby("jugador")[["bajas", "muertes", "rendimiento"]].sum().reset_index()
    ranking["ratio"] = ranking["bajas"] / ranking["muertes"].replace(0, np.nan)
    ranking = ranking.sort_values(by="rendimiento", ascending=False).reset_index(drop=True)
    st.dataframe(ranking, use_container_width=True)

# ---------------- TAB 2: Tablas Detalladas ----------------
with tab2:
    st.subheader("📋 Rendimiento Acumulado por Jugador y Mapa")

    if {"jugador", "mapa", "bajas", "muertes", "rendimiento", "ratio"}.issubset(df.columns):
        pivot = df.pivot_table(
            index="jugador",
            columns="mapa",
            values=["bajas", "muertes", "rendimiento", "ratio"],
            aggfunc="sum",
            fill_value=0
        )

        # Reordenar columnas para más claridad
        pivot = pivot.swaplevel(axis=1).sort_index(axis=1, level=0)

        # Columna total final
        pivot["Total"] = pivot.sum(axis=1, numeric_only=True)

        pivot = pivot.sort_values(by=("Total", ""), ascending=False)

        st.dataframe(pivot, use_container_width=True)
    else:
        st.warning("⚠️ No se encontraron todas las columnas necesarias para esta tabla.")

# ---------------- TAB 3: Equipos ----------------
with tab3:
    st.subheader("⚖️ Propuesta de Equipos Balanceados")
    # Aquí se puede implementar lógica para dividir en equipos (placeholder)
    st.info("🚧 Próximamente: división automática en equipos balanceados.")

# ---------------- TAB 4: Por Fecha ----------------
with tab4:
    st.subheader("🌍 Estadísticas por Jugador y Fecha")
    if "fecha" in df.columns:
        fecha_sel = st.selectbox("Selecciona una fecha", sorted(df["fecha"].dropna().unique()))
        filtro = df[df["fecha"] == fecha_sel]

        tabla_fecha = filtro.groupby("jugador")[["bajas", "muertes", "rendimiento"]].sum().reset_index()
        tabla_fecha["ratio"] = tabla_fecha["bajas"] / tabla_fecha["muertes"].replace(0, np.nan)
        tabla_fecha = tabla_fecha.sort_values(by="rendimiento", ascending=False).reset_index(drop=True)

        st.dataframe(tabla_fecha, use_container_width=True)
    else:
        st.warning("⚠️ No se encontró la columna 'fecha' en el archivo.")

# ---------------- TAB 5: Visualizaciones ----------------
with tab5:
    st.subheader("📈 Gráficos y Visualizaciones")

    # 🔥 Heatmap con Altair
    st.markdown("### 🔥 Heatmap de Rendimiento por Jugador y Mapa")

    opciones = ["Acumulado"] + sorted(df["fecha"].dropna().unique()) if "fecha" in df.columns else ["Acumulado"]
    fecha_sel = st.selectbox("Selecciona una fecha o acumulado", opciones, key="heatmap_fecha")

    if fecha_sel == "Acumulado":
        heatmap_df = df.pivot_table(
            index="jugador", columns="mapa", values="rendimiento", aggfunc="sum", fill_value=0
        ).reset_index()
    else:
        heatmap_df = df[df["fecha"] == fecha_sel].pivot_table(
            index="jugador", columns="mapa", values="rendimiento", aggfunc="sum", fill_value=0
        ).reset_index()

    heatmap_melt = heatmap_df.melt(id_vars=["jugador"], var_name="mapa", value_name="rendimiento")

    heatmap_chart = alt.Chart(heatmap_melt).mark_rect().encode(
        x=alt.X("mapa:N", title="Mapa"),
        y=alt.Y("jugador:N", title="Jugador"),
        color=alt.Color("rendimiento:Q", scale=alt.Scale(scheme="blues")),
        tooltip=["jugador", "mapa", "rendimiento"]
    ).properties(width=600, height=400)

    st.altair_chart(heatmap_chart, use_container_width=True)
