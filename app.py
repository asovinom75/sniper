import streamlit as st
import pandas as pd

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
        "Mejor: " + resumen["Mejor mapa"] + " (" + resumen["Rendimiento mejor"].map("{:,.0f}".format).str.replace(",", ".") + ")" +
        " | Peor: " + resumen["Peor mapa"] + " (" + resumen["Rendimiento peor"].map("{:,.0f}".format).str.replace(",", ".") + ")"
    )

    # --- Rankings ---
    rank_total = resumen.sort_values("Rendimiento_total", ascending=False).reset_index(drop=True)
    rank_total.insert(0, "Posición", rank_total.index + 1)

    # Formateo
    rank_total_fmt = rank_total[["Posición", "Jugador", "Fechas_jugadas","Bajas_total","Muertes_total", "Ratio","Rendimiento_total", "Promedio", "Mapas (Mejor | Peor)"]].copy()
    rank_total_fmt["Rendimiento_total"] = rank_total_fmt["Rendimiento_total"].map("{:,.0f}".format).str.replace(",", ".")
    rank_total_fmt["Promedio"] = rank_total_fmt["Promedio"].map("{:,.0f}".format).str.replace(",", ".")
    rank_total_fmt["Ratio"] = rank_total_fmt["Ratio"].map("{:,.2f}".format).str.replace(".", ",")
    rank_total_fmt["Bajas_total"] = rank_total_fmt["Bajas_total"].map("{:,.0f}".format).str.replace(",", ".")
    rank_total_fmt["Muertes_total"] = rank_total_fmt["Muertes_total"].map("{:,.0f}".format).str.replace(",", ".")

    st.subheader("🏆 Ranking con Mejor y Peor Mapa Acumulada (ordenado por Rendimiento Total)")
    st.dataframe(rank_total_fmt, use_container_width=True)

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
        df_equipo["Promedio"] = df_equipo["Promedio"].map("{:,.0f}".format).str.replace(",", ".")

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
            "Mejor: " + mapa_fecha["Mejor mapa"] + " (" + mapa_fecha["Rendimiento mejor"].map("{:,.0f}".format).str.replace(",", ".") + ")" +
            " | Peor: " + mapa_fecha["Peor mapa"] + " (" + mapa_fecha["Rendimiento peor"].map("{:,.0f}".format).str.replace(",", ".") + ")"
        )

        # Formateo
        mapa_fecha["Rendimiento_total"] = mapa_fecha["Rendimiento_total"].map("{:,.0f}".format).str.replace(",", ".")
        mapa_fecha["Promedio"] = mapa_fecha["Promedio"].map("{:,.0f}".format).str.replace(",", ".")
        mapa_fecha["Bajas_total"] = mapa_fecha["Bajas_total"].map("{:,.0f}".format).str.replace(",", ".")
        mapa_fecha["Muertes_total"] = mapa_fecha["Muertes_total"].map("{:,.0f}".format).str.replace(",", ".")

        st.dataframe(mapa_fecha[["Jugador", "Bajas_total", "Muertes_total", "Rendimiento_total", "Promedio", "Mapas (Mejor | Peor)"]], use_container_width=True)

        # --- Gráficos de la fecha seleccionada ---
        st.subheader(f"📊 Rendimiento por Jugador – Fecha {selected_fecha}")
        st.bar_chart(df_fecha.groupby("Jugador")["Rendimiento"].sum())

        st.subheader(f"📊 Bajas y Muertes – Fecha {selected_fecha}")
        bajas_muertes = df_fecha.groupby("Jugador")[["Bajas", "Muertes"]].sum()
        st.bar_chart(bajas_muertes)

    # --- Gráficos acumulados ---
    st.subheader("📊 Rendimiento Total por Jugador (Acumulado)")
    st.bar_chart(rank_total.set_index("Jugador")["Rendimiento_total"])

    st.subheader("📊 Promedio por Jugador (Acumulado)")
    st.bar_chart(rank_prom.set_index("Jugador")["Promedio"])

except FileNotFoundError:
    st.error("El archivo no se encontró. Verifica que esté en el directorio correcto.")
except Exception as e:
    st.error(f"Ocurrió un error al cargar el archivo: {e}")
