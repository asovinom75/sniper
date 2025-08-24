import streamlit as st
import pandas as pd
import altair as alt
import matplotlib.pyplot as plt
import seaborn as sns

# Configuración de página
st.set_page_config(page_title="Campeonato Sniper Elite", layout="wide")

st.title("📊 Campeonato Sniper Elite Resistencia – Dashboard")

# ------------------------
# Cargar archivo Excel
# ------------------------
archivo = "Estadiscticas Campeonato interno Sniper Elite 6_ver2.xlsx"
df = pd.read_excel(archivo, sheet_name=None)

# Los primeros 6 mapas son válidos
mapas = list(df.keys())[:6]

# Unir todos los datos en un solo DataFrame
dataframes = []
for mapa in mapas:
    tmp = df[mapa].iloc[4:, 2:].copy()  # datos desde fila 5, col C
    tmp.columns = df[mapa].iloc[3, 2:]  # fila 4 como encabezado
    tmp["Mapa"] = mapa
    dataframes.append(tmp)

df = pd.concat(dataframes, ignore_index=True)

# Convertir a numérico
for col in ["Bajas", "Muertes", "Rendimiento"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Crear columna Ratio
df["Ratio"] = df["Bajas"] / df["Muertes"].replace(0, 1)

# ------------------------
# KPIs Iniciales
# ------------------------
st.subheader("📌 Indicadores Clave del Torneo")

acum = df.groupby("Jugador").agg({"Rendimiento":"sum","Bajas":"sum","Muertes":"sum"}).reset_index()
acum["Ratio"] = acum["Bajas"] / acum["Muertes"].replace(0,1)

mejor_jugador = acum.loc[acum["Rendimiento"].idxmax(), "Jugador"]
mejor_rend = acum["Rendimiento"].max()

mejor_ratio_jugador = acum.loc[acum["Ratio"].idxmax(), "Jugador"]
mejor_ratio = acum["Ratio"].max()

prom_rend = acum["Rendimiento"].mean()

col1, col2, col3 = st.columns(3)
col1.metric("🏅 Mayor Rendimiento", mejor_jugador, f"{mejor_rend:,.0f}".replace(",", "."))
col2.metric("⚡ Mejor Ratio", mejor_ratio_jugador, f"{mejor_ratio:,.2f}".replace(".", ","))
col3.metric("📊 Rendimiento Promedio", f"{prom_rend:,.0f}".replace(",", "."))

# ------------------------
# Tabs
# ------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏆 Ranking",
    "📋 Tablas Detalladas",
    "⚖️ Equipos Balanceados",
    "🌍 Estadísticas por Fecha",
    "📈 Visualizaciones Avanzadas"
])

# ------------------------
# TAB 1: Ranking
# ------------------------
with tab1:
    st.subheader("🏆 Ranking con Mejor y Peor Mapa Acumulada")

    # Mejor y peor mapa por jugador
    resumen = df.groupby(["Jugador","Mapa"]).agg({"Rendimiento":"sum"}).reset_index()
    mejor = resumen.loc[resumen.groupby("Jugador")["Rendimiento"].idxmax()].set_index("Jugador")
    peor = resumen.loc[resumen.groupby("Jugador")["Rendimiento"].idxmin()].set_index("Jugador")

    rank_total = resumen.groupby("Jugador")["Rendimiento"].sum().reset_index()
    rank_total["Mejor Mapa"] = mejor["Mapa"].values
    rank_total["Peor Mapa"] = peor["Mapa"].values
    rank_total = rank_total.sort_values("Rendimiento", ascending=False).reset_index(drop=True)
    rank_total.index += 1

    rank_total_fmt = rank_total.copy()
    rank_total_fmt["Rendimiento"] = rank_total_fmt["Rendimiento"].apply(lambda x: f"{int(x):,}".replace(",", "."))

    st.dataframe(rank_total_fmt, use_container_width=True)

# ------------------------
# TAB 2: Tablas Detalladas
# ------------------------
with tab2:
    st.subheader("📋 Rendimiento, Bajas, Muertes y Ratio por Jugador y Mapa")

    pivot_rend = df.pivot_table(index="Jugador", columns="Mapa", values="Rendimiento", aggfunc="sum", fill_value=0)
    pivot_bajas = df.pivot_table(index="Jugador", columns="Mapa", values="Bajas", aggfunc="sum", fill_value=0)
    pivot_muertes = df.pivot_table(index="Jugador", columns="Mapa", values="Muertes", aggfunc="sum", fill_value=0)
    pivot_ratio = (pivot_bajas / pivot_muertes.replace(0,1)).round(2)

    tablas = []
    for mapa in mapas:
        df_tmp = pd.DataFrame({
            (mapa, "Rendimiento"): pivot_rend[mapa],
            (mapa, "Bajas"): pivot_bajas[mapa],
            (mapa, "Muertes"): pivot_muertes[mapa],
            (mapa, "Ratio"): pivot_ratio[mapa]
        })
        tablas.append(df_tmp)

    tabla_final = pd.concat(tablas, axis=1)
    tabla_final[("Total","Rendimiento")] = tabla_final.xs("Rendimiento", axis=1, level=1).sum(axis=1)
    tabla_final = tabla_final.sort_values(("Total","Rendimiento"), ascending=False)

    def fmt(val,tipo):
        if pd.isna(val): return ""
        if tipo=="Ratio": return f"{val:,.2f}".replace(".",",")
        else: return f"{int(val):,}".replace(",", ".")

    tabla_fmt = tabla_final.copy()
    for col in tabla_fmt.columns:
        tipo = col[1]
        tabla_fmt[col] = tabla_fmt[col].apply(lambda x: fmt(x,tipo))

    st.dataframe(tabla_fmt, use_container_width=True)

# ------------------------
# TAB 3: Equipos Balanceados
# ------------------------
with tab3:
    st.subheader("⚖️ Propuesta de Equipos Balanceados")
    jugadores = list(acum.sort_values("Rendimiento", ascending=False)["Jugador"])
    equipo1 = jugadores[::2]
    equipo2 = jugadores[1::2]
    st.write("**Equipo 1:**", ", ".join(equipo1))
    st.write("**Equipo 2:**", ", ".join(equipo2))

# ------------------------
# TAB 4: Estadísticas por Fecha
# ------------------------
with tab4:
    st.subheader("🌍 Estadísticas por Jugador y Fecha")

    fechas = df["Fecha"].dropna().unique()
    fecha_sel = st.selectbox("Selecciona una fecha", fechas)

    df_fecha = df[df["Fecha"]==fecha_sel]

    chart = alt.Chart(df_fecha).mark_bar().encode(
        x="Jugador",
        y="Rendimiento",
        color="Mapa"
    ).properties(width=700, height=400)

    st.altair_chart(chart, use_container_width=True)

# ------------------------
# TAB 5: Visualizaciones Avanzadas
# ------------------------
with tab5:
    st.subheader("📈 Comparaciones Avanzadas")

    # Radar Chart
    st.markdown("### Radar Chart de Rendimiento por Mapa")
    radar_df = resumen.pivot(index="Jugador", columns="Mapa", values="Rendimiento").fillna(0).reset_index()
    radar_df = pd.melt(radar_df, id_vars=["Jugador"], var_name="Mapa", value_name="Rendimiento")

    radar_chart = alt.Chart(radar_df).mark_line(point=True).encode(
        theta=alt.Theta("Mapa:N", sort=mapas),
        radius="Rendimiento:Q",
        color="Jugador:N"
    ).properties(width=600, height=600)

    st.altair_chart(radar_chart, use_container_width=True)

    # Heatmap
    st.markdown("### 🔥 Heatmap de Rendimiento por Jugador y Mapa")
    heatmap_df = df.pivot_table(index="Jugador", columns="Mapa", values="Rendimiento", aggfunc="sum", fill_value=0)

    fig, ax = plt.subplots(figsize=(10,6))
    sns.heatmap(heatmap_df, annot=True, fmt=".0f", cmap="YlGnBu", linewidths=0.5, cbar_kws={"label":"Rendimiento Total"})
    st.pyplot(fig)
