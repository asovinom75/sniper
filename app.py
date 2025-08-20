import streamlit as st
import pandas as pd

st.set_page_config(page_title="Ranking Campeonato", layout="wide")

st.title("📊 Campeonato Sniper Elite Resistencia – Consolidado por Jugador")

# Carga automática del archivo (asumiendo que se llama 'Estadiscticas Campeonato interno Sniper Elite 6_ver2.xlsx' y está en el mismo directorio)
archivo = "Estadiscticas Campeonato interno Sniper Elite 6_ver2.xlsx"

# Verificar si el archivo existe
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

    # Asegurarse de que 'Fecha' sea un entero (representada por números del 1 al 30)
    df['Fecha'] = df['Fecha'].astype(int)

    #st.subheader("Datos consolidados (primeras filas)")
    #st.dataframe(df.head())

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

    # Redondear
    for col in ["Rendimiento_total", "Promedio", "Rendimiento mejor", "Rendimiento peor"]:
        resumen[col] = resumen[col].round(2)

    # Columna compacta con mejor y peor mapa
    resumen["Mapas (Mejor | Peor)"] = (
        "Mejor: " + resumen["Mejor mapa"] + " (" + resumen["Rendimiento mejor"].map("{:,.0f}".format) + ")" +
        " | Peor: " + resumen["Peor mapa"] + " (" + resumen["Rendimiento peor"].map("{:,.0f}".format) + ")"
    )

    # --- Rankings ---
    rank_total = resumen.sort_values("Rendimiento_total", ascending=False).reset_index(drop=True)
    rank_total.insert(0, "Posición", rank_total.index + 1)

    # Formateo
    rank_total_fmt = rank_total[["Posición", "Jugador", "Fechas_jugadas","Bajas_total","Muertes_total", "Ratio","Rendimiento_total", "Promedio", "Mapas (Mejor | Peor)"]].copy()
    rank_total_fmt["Rendimiento_total"] = rank_total_fmt["Rendimiento_total"].map("{:,.0f}".format)
    rank_total_fmt["Promedio"] = rank_total_fmt["Promedio"].map("{:,.0f}".format)
    rank_total_fmt["Ratio"] = rank_total_fmt["Ratio"].map("{:,.2f}".format)
    st.subheader("🏆 Ranking con Mejor y Peor Mapa Acumulada (ordenado por Rendimiento Total)")
    st.dataframe(rank_total_fmt)

    # --- Balance de equipos (solo promedio) ---
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
        df_equipo["Promedio"] = df_equipo["Promedio"].map("{:,.0f}".format)

    st.subheader("⚖️ Equipos Balanceados (por promedio)")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Equipo A")
        st.dataframe(dfA)
        st.markdown(f"**TOTAL Promedio: {promA:,.0f}**")

    with col2:
        st.markdown("### Equipo B")
        st.dataframe(dfB)
        st.markdown(f"**TOTAL Promedio: {promB:,.0f}**")

    # --- Mejor y Peor mapa por jugador y fecha ---
    mejor_fecha_mapa = (
        df.loc[df.groupby(["Jugador", "Fecha"])["Rendimiento"].idxmax()]
        [["Jugador", "Fecha", "Mapa", "Rendimiento"]]
        .reset_index(drop=True)
        .rename(columns={"Mapa": "Mejor mapa", "Rendimiento": "Rendimiento mejor"})
    )
    peor_fecha_mapa = (
        df.loc[df.groupby(["Jugador", "Fecha"])["Rendimiento"].idxmin()]
        [["Jugador", "Fecha", "Mapa", "Rendimiento"]]
        .reset_index(drop=True)
        .rename(columns={"Mapa": "Peor mapa", "Rendimiento": "Rendimiento peor"})
    )

    # Unir mejor y peor mapa en la misma tabla
    mapa_fecha = mejor_fecha_mapa.merge(peor_fecha_mapa, on=["Jugador", "Fecha"], how="left")

    # Redondear y formatear
    for col in ["Rendimiento mejor", "Rendimiento peor"]:
        mapa_fecha[col] = mapa_fecha[col].round(2).map("{:,.0f}".format)

    st.subheader("🌍 Estadísticas por Jugador y Fecha (Mejor y Peor Mapa)")
    st.dataframe(mapa_fecha)

    # --- Nueva sección: Estadísticas por fecha con filtro ---
    st.subheader("📅 Estadísticas por Fecha")

    # Obtener fechas únicas y ordenarlas numéricamente
    unique_fechas = sorted(df['Fecha'].unique())

    # Filtro de fecha
    selected_fecha = st.selectbox("Selecciona una fecha", unique_fechas)

    if selected_fecha:
        df_fecha = df[df['Fecha'] == selected_fecha]

        # Consolidación por jugador en la fecha seleccionada
        resumen_fecha = (
            df_fecha.groupby("Jugador")
            .agg(
                Rendimiento_total=("Rendimiento", "sum"),
                Mapas_jugados=("Mapa", "nunique")
            )
            .reset_index()
        )
        resumen_fecha["Promedio"] = (resumen_fecha["Rendimiento_total"] / resumen_fecha["Mapas_jugados"]).round(2)

        # Ordenar por Rendimiento_total descendente
        resumen_fecha = resumen_fecha.sort_values("Rendimiento_total", ascending=False).reset_index(drop=True)

        # Formateo
        resumen_fecha_fmt = resumen_fecha.copy()
        resumen_fecha_fmt["Rendimiento_total"] = resumen_fecha_fmt["Rendimiento_total"].map("{:,.0f}".format)
        resumen_fecha_fmt["Promedio"] = resumen_fecha_fmt["Promedio"].map("{:,.0f}".format)

        st.dataframe(resumen_fecha_fmt)

        # Indicar mejor y peor jugador
        if not resumen_fecha.empty:
            mejor_jugador = resumen_fecha.iloc[0]["Jugador"]
            peor_jugador = resumen_fecha.iloc[-1]["Jugador"]
            st.markdown(f"**Mejor rendimiento:** {mejor_jugador} (Rendimiento total: {resumen_fecha.iloc[0]['Rendimiento_total']:.0f})")
            st.markdown(f"**Peor rendimiento:** {peor_jugador} (Rendimiento total: {resumen_fecha.iloc[-1]['Rendimiento_total']:.0f})")

    # --- Gráficos ---
    st.subheader("📊 Rendimiento Total por Jugador")
    st.bar_chart(rank_total.set_index("Jugador")["Rendimiento_total"])

    st.subheader("📊 Promedio por Jugador")
    st.bar_chart(rank_prom.set_index("Jugador")["Promedio"])

except FileNotFoundError:
    st.error("El archivo 'Estadiscticas Campeonato interno Sniper Elite 6_ver2.xlsx' no se encontró. Asegúrate de que esté en el directorio correcto.")
except Exception as e:
    st.error(f"Ocurrió un error al cargar el archivo: {e}")
