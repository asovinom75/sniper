import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Ranking Campeonato", layout="wide")

st.title("📊 Campeonato Sniper Elite Resistencia – Consolidado por Jugador")

archivo = "Estadiscticas Campeonato interno Sniper Elite 6_ver2.xlsx"

try:
    xls = pd.ExcelFile(archivo)
    hojas = xls.sheet_names

    # Tomar solo las primeras 6 hojas (mapas)
    mapas = hojas[:6]

    # Leer y unir (agregando columna Mapa)
    df = pd.concat(
        [pd.read_excel(archivo, sheet_name=h).assign(Mapa=h) for h in mapas],
        ignore_index=True
    )

    # Asegurarse de que 'Fecha' sea entero
    df['Fecha'] = df['Fecha'].astype(int)

    # --- Consolidación por jugador ---
    resumen = (
        df.groupby("Jugador")
        .agg(
            Fechas_jugadas=("Fecha", "nunique"),
            Rendimiento_total=("Rendimiento", "sum"),
            Bajas_total=("Bajas", "sum"),
            Muertes_total=("Muertes", "sum")
        )
        .reset_index()
    )
    resumen["Promedio"] = resumen["Rendimiento_total"] / resumen["Fechas_jugadas"]
    resumen["Ratio"] = resumen["Bajas_total"] / resumen["Muertes_total"]

    # Mejor mapa acumulada
    acumulado_mapa = df.groupby(["Jugador", "Mapa"])["Rendimiento"].sum().reset_index()
    mejor_mapa_acum = (
        acumulado_mapa.loc[acumulado_mapa.groupby("Jugador")["Rendimiento"].idxmax()]
        .reset_index(drop=True)
        .rename(columns={"Mapa": "Mejor mapa", "Rendimiento": "Rendimiento mejor"})
    )

    # Peor mapa acumulada
    peor_mapa_acum = (
        acumulado_mapa.loc[acumulado_mapa.groupby("Jugador")["Rendimiento"].idxmin()]
        .reset_index(drop=True)
        .rename(columns={"Mapa": "Peor mapa", "Rendimiento": "Rendimiento peor"})
    )

    # Unir con el resumen
    resumen = resumen.merge(mejor_mapa_acum, on="Jugador", how="left")
    resumen = resumen.merge(peor_mapa_acum, on="Jugador", how="left")

    # Columna compacta con mejor y peor mapa
    resumen["Mapas (Mejor | Peor)"] = (
        "Mejor: " + resumen["Mejor mapa"] + " (" + resumen["Rendimiento mejor"].map("{:,.0f}".format).str.replace(",", ".", regex=False) + ")" +
        " | Peor: " + resumen["Peor mapa"] + " (" + resumen["Rendimiento peor"].map("{:,.0f}".format).str.replace(",", ".", regex=False) + ")"
    )

    # --- Rankings ---
    rank_total = resumen.sort_values("Rendimiento_total", ascending=False).reset_index(drop=True)
    rank_total.insert(0, "Posición", rank_total.index + 1)

    # Formateo
    rank_total_fmt = rank_total[["Posición", "Jugador", "Fechas_jugadas","Bajas_total","Muertes_total", "Ratio","Rendimiento_total", "Promedio", "Mapas (Mejor | Peor)"]].copy()
    rank_total_fmt["Rendimiento_total"] = rank_total_fmt["Rendimiento_total"].map("{:,.0f}".format).str.replace(",", ".", regex=False)
    rank_total_fmt["Promedio"] = rank_total_fmt["Promedio"].map("{:,.2f}".format).str.replace(".", ",", regex=False)
    rank_total_fmt["Ratio"] = rank_total_fmt["Ratio"].map("{:,.2f}".format).str.replace(".", ",", regex=False)
    rank_total_fmt["Bajas_total"] = rank_total_fmt["Bajas_total"].map("{:,.0f}".format).str.replace(",", ".", regex=False)
    rank_total_fmt["Muertes_total"] = rank_total_fmt["Muertes_total"].map("{:,.0f}".format).str.replace(",", ".", regex=False)

    st.subheader("🏆 Ranking con Mejor y Peor Mapa Acumulada (ordenado por Rendimiento Total)")
    st.dataframe(rank_total_fmt, use_container_width=True)

    # --- Segunda tabla: Rendimiento, Bajas, Muertes y Ratio por Jugador y Mapa ---
    st.subheader("📋 Rendimiento, Bajas, Muertes y Ratio por Jugador y Mapa")

    # Pivot rendimiento, bajas y muertes
    pivot_rend = df.pivot_table(index="Jugador", columns="Mapa", values="Rendimiento", aggfunc="sum", fill_value=0)
    pivot_bajas = df.pivot_table(index="Jugador", columns="Mapa", values="Bajas", aggfunc="sum", fill_value=0)
    pivot_muertes = df.pivot_table(index="Jugador", columns="Mapa", values="Muertes", aggfunc="sum", fill_value=0)

    # Calcular ratio = bajas/muertes (por mapa)
    pivot_ratio = pivot_bajas / pivot_muertes.replace(0, 1)  # evitar división por 0
    pivot_ratio = pivot_ratio.round(2)

    # Construir tabla final combinando métricas
    tablas = []
    for mapa in mapas:  # mantener orden de hojas[:6]
        df_tmp = pd.DataFrame({
            (mapa, "Rendimiento"): pivot_rend[mapa],
            (mapa, "Bajas"): pivot_bajas[mapa],
            (mapa, "Muertes"): pivot_muertes[mapa],
            (mapa, "Ratio"): pivot_ratio[mapa]
        })
        tablas.append(df_tmp)

    tabla_final = pd.concat(tablas, axis=1)

    # Agregar total rendimiento al final
    tabla_final[("Total", "Rendimiento")] = tabla_final.xs("Rendimiento", axis=1, level=1).sum(axis=1)

    # Ordenar por rendimiento total
    tabla_final = tabla_final.sort_values(("Total", "Rendimiento"), ascending=False)

    # Formateo: miles con punto y ratio con coma
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

    st.dataframe(tabla_fmt, use_container_width=True)

    # --- Balance de equipos ---
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

    for df_equipo in [dfA, dfB]:
        df_equipo["Promedio"] = df_equipo["Promedio"].map("{:,.0f}".format).str.replace(",", ".", regex=False)

    st.subheader("⚖️ Equipos Balanceados (por promedio)")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Equipo A")
        st.dataframe(dfA, use_container_width=True)
        st.markdown(f"**TOTAL Promedio: {promA:,.0f}**".replace(",", "."))
    with col2:
        st.markdown("### Equipo B")
        st.dataframe(dfB, use_container_width=True)
        st.markdown(f"**TOTAL Promedio: {promB:,.0f}**".replace(",", "."))

    # --- Estadísticas por Jugador y Fecha ---
    st.subheader("🌍 Estadísticas por Jugador y Fecha (Mejor y Peor Mapa)")

    # Filtro de fecha
    unique_fechas = sorted(df['Fecha'].unique())
    selected_fecha = st.selectbox("Selecciona una fecha", unique_fechas)

    if selected_fecha:
        df_fecha = df[df['Fecha'] == selected_fecha]

        # Mejor y peor mapa en la fecha seleccionada
        mejor_fecha_mapa = (
            df_fecha.loc[df_fecha.groupby("Jugador")["Rendimiento"].idxmax()]
            [["Jugador", "Mapa", "Rendimiento"]]
            .rename(columns={"Mapa": "Mejor mapa", "Rendimiento": "Rendimiento mejor"})
        )
        peor_fecha_mapa = (
            df_fecha.loc[df_fecha.groupby("Jugador")["Rendimiento"].idxmin()]
            [["Jugador", "Mapa", "Rendimiento"]]
            .rename(columns={"Mapa": "Peor mapa", "Rendimiento": "Rendimiento peor"})
        )

        # Consolidación con bajas y muertes
        resumen_fecha = (
            df_fecha.groupby("Jugador")
            .agg(
                Bajas_total=("Bajas", "sum"),
                Muertes_total=("Muertes", "sum"),
                Rendimiento_total=("Rendimiento", "sum"),
                Mapas_jugados=("Mapa", "nunique")
            )
            .reset_index()
        )
        resumen_fecha["Promedio"] = (resumen_fecha["Rendimiento_total"] / resumen_fecha["Mapas_jugados"]).round(2)

        # Unir mejor y peor mapa
        mapa_fecha = resumen_fecha.merge(mejor_fecha_mapa, on="Jugador", how="left").merge(peor_fecha_mapa, on="Jugador", how="left")

        # Columna combinada mejor | peor
        mapa_fecha["Mapas (Mejor | Peor)"] = (
            "Mejor: " + mapa_fecha["Mejor mapa"] + " (" + mapa_fecha["Rendimiento mejor"].map("{:,.0f}".format).str.replace(",", ".", regex=False) + ")" +
            " | Peor: " + mapa_fecha["Peor mapa"] + " (" + mapa_fecha["Rendimiento peor"].map("{:,.0f}".format).str.replace(",", ".", regex=False) + ")"
        )

        # Formateo
        mapa_fecha["Rendimiento_total"] = mapa_fecha["Rendimiento_total"].map("{:,.0f}".format).str.replace(",", ".", regex=False)
        mapa_fecha["Promedio"] = mapa_fecha["Promedio"].map("{:,.0f}".format).str.replace(",", ".", regex=False)
        mapa_fecha["Bajas_total"] = mapa_fecha["Bajas_total"].map("{:,.0f}".format).str.replace(",", ".", regex=False)
        mapa_fecha["Muertes_total"] = mapa_fecha["Muertes_total"].map("{:,.0f}".format).str.replace(",", ".", regex=False)

        st.dataframe(mapa_fecha[["Jugador", "Bajas_total", "Muertes_total", "Rendimiento_total", "Promedio", "Mapas (Mejor | Peor)"]], use_container_width=True)

        # --- Gráficos de la fecha seleccionada con Altair ---
        st.subheader(f"📊 Rendimiento por Jugador – Fecha {selected_fecha}")
        chart_rend = alt.Chart(df_fecha).mark_bar().encode(
            x=alt.X("Jugador:N", sort="-y"),
            y="sum(Rendimiento):Q",
            tooltip=["Jugador", "sum(Rendimiento)"]
        )
        st.altair_chart(chart_rend, use_container_width=True)

        st.subheader(f"📊 Bajas y Muertes – Fecha {selected_fecha}")
        bajas_muertes = df_fecha.groupby("Jugador")[["Bajas", "Muertes"]].sum().reset_index()
        bajas_muertes_melt = bajas_muertes.melt("Jugador", var_name="Tipo", value_name="Cantidad")
        chart_bm = alt.Chart(bajas_muertes_melt).mark_bar().encode(
            x=alt.X("Jugador:N", sort="-y"),
            y="Cantidad:Q",
            color="Tipo:N",
            tooltip=["Jugador", "Tipo", "Cantidad"]
        )
        st.altair_chart(chart_bm, use_container_width=True)

    # --- Gráficos acumulados con Altair ---
    st.subheader("📊 Rendimiento Total por Jugador (Acumulado)")
    chart_total = alt.Chart(rank_total).mark_bar().encode(
        x=alt.X("Jugador:N", sort="-y"),
        y="Rendimiento_total:Q",
        tooltip=["Jugador", "Rendimiento_total"]
    )
    st.altair_chart(chart_total, use_container_width=True)

    st.subheader("📊 Promedio por Jugador (Acumulado)")
    chart_prom = alt.Chart(rank_prom).mark_bar().encode(
        x=alt.X("Jugador:N", sort="-y"),
        y="Promedio:Q",
        tooltip=["Jugador", "Promedio"]
    )
    st.altair_chart(chart_prom, use_container_width=True)

except FileNotFoundError:
    st.error("El archivo no se encontró. Verifica que esté en el directorio correcto.")
except Exception as e:
    st.error(f"Ocurrió un error al cargar el archivo: {e}")

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
