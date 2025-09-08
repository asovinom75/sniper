import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Ranking Campeonato", layout="wide")

st.title("📊 Campeonato Sniper Elite Resistencia – Consolidado por Jugador")

archivo = "Estadiscticas Campeonato interno Sniper Elite 6_ver2.xlsx"

try:
    xls = pd.ExcelFile(archivo)
    hojas = xls.sheet_names
    mapas = hojas[:6]

    df = pd.concat(
        [pd.read_excel(archivo, sheet_name=h).assign(Mapa=h) for h in mapas],
        ignore_index=True
    )

    df['Fecha'] = df['Fecha'].astype(int)

    # --- Bonus por Partida Ganada (solo una vez por fecha) ---
    if "Partida Ganada" in df.columns:
        # Total de partidas ganadas por jugador y fecha (sumando los 6 mapas)
        partidas_por_fecha = (
            df.groupby(["Fecha", "Jugador"])["Partida Ganada"]
            .sum()
            .reset_index()
        )

        # Identificar máximo de partidas ganadas por fecha
        max_por_fecha = (
            partidas_por_fecha.groupby("Fecha")["Partida Ganada"]
            .transform("max")
        )

        # Marcar a los jugadores que alcanzaron ese máximo
        partidas_por_fecha["Es_ganador_fecha"] = partidas_por_fecha["Partida Ganada"] == max_por_fecha

        # Asignar bonus de 600 puntos solo a esos jugadores
        partidas_por_fecha["Bonus"] = partidas_por_fecha["Es_ganador_fecha"].astype(int) * 600

        # Sumar bonus por jugador en todo el campeonato
        bonus_por_jugador = partidas_por_fecha.groupby("Jugador")["Bonus"].sum().reset_index()

        # Incorporar bonus al dataframe original
        df = df.merge(bonus_por_jugador, on="Jugador", how="left")
        df["Bonus"] = df["Bonus"].fillna(0)

        # Ajustar rendimiento con bonus
        df["Rendimiento"] = df["Rendimiento"] + df["Bonus"]

    else:
        df["Bonus"] = 0

    # --- Consolidación por jugador ---
    resumen = (
        df.groupby("Jugador")
        .agg(
            Fechas_jugadas=("Fecha", "nunique"),
            Rendimiento_total=("Rendimiento", "sum"),
            Bajas_total=("Bajas", "sum"),
            Muertes_total=("Muertes", "sum"),
            Bonus_total=("Bonus", "max")  # se usa max porque el valor ya es total por jugador
        )
        .reset_index()
    )
    resumen["Promedio"] = resumen["Rendimiento_total"] / resumen["Fechas_jugadas"]
    resumen["Ratio"] = resumen["Bajas_total"] / resumen["Muertes_total"]

    acumulado_mapa = df.groupby(["Jugador", "Mapa"])["Rendimiento"].sum().reset_index()
    mejor_mapa_acum = (
        acumulado_mapa.loc[acumulado_mapa.groupby("Jugador")["Rendimiento"].idxmax()]
        .reset_index(drop=True)
        .rename(columns={"Mapa": "Mejor mapa", "Rendimiento": "Rendimiento mejor"})
    )
    peor_mapa_acum = (
        acumulado_mapa.loc[acumulado_mapa.groupby("Jugador")["Rendimiento"].idxmin()]
        .reset_index(drop=True)
        .rename(columns={"Mapa": "Peor mapa", "Rendimiento": "Rendimiento peor"})
    )

    resumen = resumen.merge(mejor_mapa_acum, on="Jugador", how="left")
    resumen = resumen.merge(peor_mapa_acum, on="Jugador", how="left")

    resumen["Mapas (Mejor | Peor)"] = (
        "Mejor: " + resumen["Mejor mapa"] + " (" + resumen["Rendimiento mejor"].map("{:,.0f}".format).str.replace(",", ".", regex=False) + ")" +
        " | Peor: " + resumen["Peor mapa"] + " (" + resumen["Rendimiento peor"].map("{:,.0f}".format).str.replace(",", ".", regex=False) + ")"
    )

    rank_total = resumen.sort_values("Rendimiento_total", ascending=False).reset_index(drop=True)
    rank_total.insert(0, "Posición", rank_total.index + 1)

    # ------------------ SELECCIÓN DE JUGADOR ------------------
    st.sidebar.header("🎮 Filtros")
    jugador_sel = st.sidebar.selectbox("Selecciona un jugador", ["(Todos)"] + list(resumen["Jugador"].unique()))

    if jugador_sel == "(Todos)":
        df_filtrado = df.copy()
        res_filtrado = resumen.copy()
    else:
        df_filtrado = df[df["Jugador"] == jugador_sel]
        res_filtrado = resumen[resumen["Jugador"] == jugador_sel]

    # --- KPI’s grandes en top ---
    st.markdown("## 🔑 KPI’s Acumulados")
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    bajas = res_filtrado["Bajas_total"].sum()
    muertes = res_filtrado["Muertes_total"].sum()
    rend = res_filtrado["Rendimiento_total"].sum()
    prom = res_filtrado["Promedio"].mean()
    ratio = res_filtrado["Ratio"].mean()
    bonus_total = res_filtrado["Bonus_total"].sum()

    col1.metric("Bajas", f"{bajas:,}".replace(",", "."))
    col2.metric("Muertes", f"{muertes:,}".replace(",", "."))
    col3.metric("Rendimiento", f"{rend:,}".replace(",", "."))
    col4.metric("Promedio", f"{prom:,.0f}".replace(".", ","))
    col5.metric("Ratio", f"{ratio:,.2f}".replace(".", ","))
    col6.metric("Bonus", f"{bonus_total:,}".replace(",", "."))

    # ------------------ TABS ------------------
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏆 Ranking", 
        "📋 Rendimiento por Mapa", 
        "⚖️ Balance de Equipos", 
        "🌍 Estadísticas por Fecha", 
        "📊 Gráficos Acumulados"
    ])

    # TAB 1 - Ranking
    with tab1:
        st.subheader("🏆 Ranking con Mejor y Peor Mapa (Acumulado)")
        st.dataframe(
            rank_total[
                ["Posición","Jugador","Fechas_jugadas","Bajas_total","Muertes_total","Ratio","Rendimiento_total","Promedio","Bonus_total","Mapas (Mejor | Peor)"]
            ],
            use_container_width=True
        )

    # TAB 2 - Rendimiento por Jugador y Mapa
    with tab2:
        st.subheader("📋 Rendimiento, Bajas, Muertes y Ratio por Jugador y Mapa")

        pivot_rend = df.pivot_table(index="Jugador", columns="Mapa", values="Rendimiento", aggfunc="sum", fill_value=0)
        pivot_bajas = df.pivot_table(index="Jugador", columns="Mapa", values="Bajas", aggfunc="sum", fill_value=0)
        pivot_muertes = df.pivot_table(index="Jugador", columns="Mapa", values="Muertes", aggfunc="sum", fill_value=0)
        pivot_ratio = (pivot_bajas / pivot_muertes.replace(0, 1)).round(2)

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

        st.dataframe(tabla_final, use_container_width=True)

    # TAB 3 - Balance de equipos
    with tab3:
        st.subheader("⚖️ Equipos Balanceados (por promedio)")

        equipoA, equipoB = [], []
        promA, promB = 0, 0
        rank_prom = resumen.sort_values("Promedio", ascending=False).reset_index(drop=True)

        for i, row in rank_prom.iterrows():
            if i % 2 == 0:
                equipoA.append(row)
                promA += row["Promedio"]
            else:
                equipoB.append(row)
                promB += row["Promedio"]

        dfA = pd.DataFrame(equipoA)[["Jugador", "Promedio"]]
        dfB = pd.DataFrame(equipoB)[["Jugador", "Promedio"]]

        col1, col2 = st.columns(2)
        col1.metric("Promedio Equipo A", f"{promA:,.0f}".replace(",", "."))
        col2.metric("Promedio Equipo B", f"{promB:,.0f}".replace(",", "."))

        col1.dataframe(dfA, use_container_width=True)
        col2.dataframe(dfB, use_container_width=True)

    # TAB 4 - Estadísticas por Jugador y Fecha
    with tab4:
        st.subheader("🌍 Estadísticas por Jugador y Fecha")

        unique_fechas = sorted(df['Fecha'].unique())
        selected_fecha = st.selectbox("Selecciona una fecha", unique_fechas)

        if selected_fecha:
            df_fecha = df[df['Fecha'] == selected_fecha]

            # KPI de fecha
            col1, col2, col3 = st.columns(3)
            col1.metric("Bajas", f"{df_fecha['Bajas'].sum():,}".replace(",", "."))
            col2.metric("Muertes", f"{df_fecha['Muertes'].sum():,}".replace(",", "."))
            col3.metric("Rendimiento", f"{df_fecha['Rendimiento'].sum():,}".replace(",", "."))

            st.dataframe(df_fecha, use_container_width=True)

    # TAB 5 - Gráficos acumulados
    with tab5:
        st.subheader("📊 Gráficos Acumulados")

        chart_total = alt.Chart(rank_total).mark_bar().encode(
            x=alt.X("Jugador:N", sort="-y"),
            y="Rendimiento_total:Q"
        )
        st.altair_chart(chart_total, use_container_width=True)

        chart_prom = alt.Chart(rank_total).mark_bar().encode(
            x=alt.X("Jugador:N", sort="-y"),
            y="Promedio:Q"
        )
        st.altair_chart(chart_prom, use_container_width=True)

except FileNotFoundError:
    st.error("El archivo no se encontró. Verifica que esté en el directorio correcto.")
except Exception as e:
    st.error(f"Ocurrió un error al cargar el archivo: {e}")
