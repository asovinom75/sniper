import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Ranking Campeonato", layout="wide")

st.title("📊 Campeonato Sniper Elite Resistencia – Consolidado por Jugador")

# --- Carga de archivo ---
archivo = "Estadiscticas Campeonato interno Sniper Elite 6_ver2.xlsx"
xls = pd.ExcelFile(archivo)
mapas = xls.sheet_names[:6]  # Los primeros 6 son mapas
df_list = []

for mapa in mapas:
    df_tmp = pd.read_excel(archivo, sheet_name=mapa, skiprows=4, usecols="C:H")
    df_tmp["Mapa"] = mapa
    df_list.append(df_tmp)

df = pd.concat(df_list)
df = df.rename(columns={"Jugador": "Jugador", "Bajas": "Bajas", "Muertes": "Muertes", "Rendimiento": "Rendimiento"})
df["Ratio"] = df["Bajas"] / df["Muertes"].replace(0, 1)

# --- KPIs ---
st.subheader("📌 Indicadores Clave del Campeonato")

df_total = df.groupby("Jugador").agg({"Rendimiento": "sum", "Bajas": "sum", "Muertes": "sum"}).reset_index()
df_total["Ratio"] = df_total["Bajas"] / df_total["Muertes"].replace(0, 1)

mejor_rend = df_total.loc[df_total["Rendimiento"].idxmax()]
mas_bajas = df_total.loc[df_total["Bajas"].idxmax()]
mejor_ratio = df_total.loc[df_total["Ratio"].idxmax()]

col1, col2, col3 = st.columns(3)
col1.metric("Mejor Rendimiento", mejor_rend["Jugador"], f"{mejor_rend['Rendimiento']:,.0f}".replace(",", "."))
col2.metric("Más Bajas", mas_bajas["Jugador"], f"{mas_bajas['Bajas']:,.0f}".replace(",", "."))
col3.metric("Mejor Ratio", mejor_ratio["Jugador"], f"{mejor_ratio['Ratio']:.2f}".replace(".", ","))

# --- Pestañas ---
tab1, tab2, tab3, tab4 = st.tabs(["🏆 Ranking General", "📋 Rendimiento por Mapa", "🗓️ Rendimiento por Fecha", "🤝 Balance de Equipos"])

# --- TAB 1: Ranking General ---
with tab1:
    st.subheader("🏆 Ranking con Mejor y Peor Mapa Acumulada (ordenado por Rendimiento Total)")
    rank_total = df.groupby("Jugador").agg(
        Total_Rendimiento=("Rendimiento", "sum"),
        Mejor_Mapa=("Rendimiento", "max"),
        Peor_Mapa=("Rendimiento", "min")
    ).sort_values("Total_Rendimiento", ascending=False).reset_index()

    # Formato
    def fmt_miles(x):
        return f"{int(x):,}".replace(",", ".")

    rank_total_fmt = rank_total.copy()
    for col in ["Total_Rendimiento", "Mejor_Mapa", "Peor_Mapa"]:
        rank_total_fmt[col] = rank_total_fmt[col].apply(fmt_miles)

    st.dataframe(rank_total_fmt.style.background_gradient(
        subset=["Total_Rendimiento"], cmap="Greens"
    ), use_container_width=True)

# --- TAB 2: Rendimiento por Mapa ---
with tab2:
    st.subheader("📋 Rendimiento, Bajas, Muertes y Ratio por Jugador y Mapa")

    pivot_rend = df.pivot_table(index="Jugador", columns="Mapa", values="Rendimiento", aggfunc="sum", fill_value=0)
    pivot_bajas = df.pivot_table(index="Jugador", columns="Mapa", values="Bajas", aggfunc="sum", fill_value=0)
    pivot_muertes = df.pivot_table(index="Jugador", columns="Mapa", values="Muertes", aggfunc="sum", fill_value=0)
    pivot_ratio = pivot_bajas / pivot_muertes.replace(0, 1)
    pivot_ratio = pivot_ratio.round(2)

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
    tabla_final[("Total", "Rendimiento")] = tabla_final.xs("Rendimiento", axis=1, level=1).sum(axis=1)
    tabla_final = tabla_final.sort_values(("Total", "Rendimiento"), ascending=False)

    # Formato
    def fmt(val, tipo):
        if pd.isna(val):
            return ""
        if tipo == "Ratio":
            return f"{val:,.2f}".replace(".", ",")
        else:
            return f"{int(val):,}".replace(",", ".")

    tabla_fmt = tabla_final.copy()
    for col in tabla_fmt.columns:
        tipo = col[1]
        tabla_fmt[col] = tabla_fmt[col].apply(lambda x: fmt(x, tipo))

    st.dataframe(tabla_final.style.background_gradient(
        cmap="Greens", subset=pd.IndexSlice[:, pd.IndexSlice[:, "Rendimiento"]]
    ).background_gradient(
        cmap="Blues", subset=pd.IndexSlice[:, pd.IndexSlice[:, "Bajas"]]
    ).background_gradient(
        cmap="Reds", subset=pd.IndexSlice[:, pd.IndexSlice[:, "Muertes"]]
    ), use_container_width=True)

# --- TAB 3: Rendimiento por Fecha ---
with tab3:
    st.subheader("🗓️ Rendimiento por Jugador y Fecha")

    fechas = xls.sheet_names[6:]
    if fechas:
        selected_fecha = st.selectbox("Selecciona una fecha", fechas)
        df_fecha = pd.read_excel(archivo, sheet_name=selected_fecha, skiprows=4, usecols="C:H")

        df_fecha["Ratio"] = df_fecha["Bajas"] / df_fecha["Muertes"].replace(0, 1)

        st.dataframe(df_fecha.style.background_gradient(cmap="Greens", subset=["Rendimiento"]), use_container_width=True)

        chart = alt.Chart(df_fecha).mark_bar().encode(
            x=alt.X("Jugador:N", sort="-y"),
            y=alt.Y("Rendimiento:Q"),
            tooltip=["Jugador", "Bajas", "Muertes", "Rendimiento", "Ratio"]
        )
        st.altair_chart(chart, use_container_width=True)

# --- TAB 4: Balance de Equipos ---
with tab4:
    st.subheader("🤝 Balance de Equipos")

    rendimiento_total = df.groupby("Jugador")["Rendimiento"].sum().reset_index()
    rendimiento_total = rendimiento_total.sort_values("Rendimiento", ascending=False).reset_index(drop=True)

    equipo1 = rendimiento_total.iloc[::2]
    equipo2 = rendimiento_total.iloc[1::2]

    col1, col2 = st.columns(2)
    col1.write("**Equipo 1**")
    col1.dataframe(equipo1.style.background_gradient(cmap="Greens", subset=["Rendimiento"]), use_container_width=True)
    col2.write("**Equipo 2**")
    col2.dataframe(equipo2.style.background_gradient(cmap="Greens", subset=["Rendimiento"]), use_container_width=True)
