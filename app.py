
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests
import matplotlib.pyplot as plt
import streamlit as st

from goes_plots import (
    plot_goes_band_chile,
    descargar_goes_aws,
    descargar_glm_aws,
    descargar_goes_serie_aws,
    descargar_goes_ultima_hora_aws,
)


# ---------------------------
# CONFIGURACIÓN BÁSICA
# ---------------------------
st.set_page_config(
    page_title="Dashboard Meteorológico Interactivo",
    layout="wide",
)

st.title("🌤️ Dashboard Meteorológico Interactivo")
st.caption("Versión demo – listo para integrar GOES-19, ERA5 y estaciones.")


# ---------------------------
# SIDEBAR – CONTROLES
# ---------------------------

st.sidebar.header("Filtros")

hoy = datetime.utcnow().date()

fecha_goes = st.sidebar.date_input("Fecha GOES", hoy)
hora_goes = st.sidebar.selectbox("Hora GOES (UTC)", list(range(0, 24)), index=0)
banda_goes = st.sidebar.selectbox("Banda GOES", [13, 8, 2], index=0)
st.sidebar.markdown("---")

# Para las secciones demo (estaciones / resumen) usamos un rango de fechas sencillo
st.sidebar.write("**Datos (demo) de estaciones:**")
fecha_inicio = fecha_goes
fecha_fin = st.sidebar.date_input("Fecha fin (series demo)", hoy)

variable_principal = st.sidebar.selectbox(
    "Variable principal",
    ["Top nuboso (°C)", "Precipitación (mm)", "Viento 200 hPa", "Viento superficie", "CAPE"],
)

st.sidebar.markdown("---")
st.sidebar.write("**Fuente de datos (demo):**")
st.sidebar.checkbox("GOES-19", value=True, disabled=True)
st.sidebar.checkbox("ERA5 / ERAS-Land", value=True, disabled=True)
st.sidebar.checkbox("Estaciones superficie", value=True, disabled=True)
st.sidebar.markdown("---")

# ---------------------------
# DATOS DEMO DE ESTACIONES
# ---------------------------

np.random.seed(42)
fechas_demo = pd.date_range(
    datetime.combine(fecha_inicio, datetime.min.time()),
    datetime.combine(fecha_fin, datetime.min.time()),
    freq="6H",
)

estaciones = ["Estación A", "Estación B", "Estación C"]
data_est = []

for est in estaciones:
    for f in fechas_demo:
        data_est.append(
            {
                "fecha": f,
                "estacion": est,
                "temp": 10 + 10 * np.random.rand(),
                "pp": max(0, np.random.randn() * 2),
                "viento": 5 + 5 * np.random.rand(),
            }
        )

df_est = pd.DataFrame(data_est)

coords_est = pd.DataFrame(
    {
        "lat": [-30.1, -30.3, -30.5],
        "lon": [-70.7, -70.9, -71.1],
        "estacion": estaciones,
    }
)

# ---------------------------
# TABS
# ---------------------------

tab_sat, tab_est, tab_resumen = st.tabs(["🛰️ Satélite", "📡 Estaciones", "📊 Resumen"])

# ---------------------------
# TAB 1: SATÉLITE (GOES DIRECTO)
# ---------------------------
with tab_sat:
    st.subheader("GOES-19 directo desde AWS – Dominio Chile")

    # Parámetros de fecha / hora / banda
    fecha = fecha_goes
    doy   = fecha.timetuple().tm_yday
    hora  = hora_goes
    banda = banda_goes

    # Checkbox ÚNICO para GLM
    mostrar_glm = st.checkbox("Mostrar actividad eléctrica (GLM)", value=False)

    # Región / dominio
    region = st.sidebar.selectbox(
        "Región / Dominio",
        ["Chile Continental", "Chile Central", "Isla de Pascua", "Zoom manual"],
    )

    dominios_predef = {
        "Chile Continental": [-85.0, -60.0, -60.0, -15.0],
        "Chile Central":     [-75.0, -67.0, -35.0, -30.0],
        "Isla de Pascua":    [-120.0, -103.0, -35.0, -20.0],
    }

    if region in dominios_predef:
        domain = dominios_predef[region]
    else:
        st.sidebar.markdown("**Zoom manual (lon/lat)**")
        lon_min = st.sidebar.number_input("Lon mínima (°W)", value=-80.0, step=0.5)
        lon_max = st.sidebar.number_input("Lon máxima (°W)", value=-65.0, step=0.5)
        lat_min = st.sidebar.number_input("Lat mínima (°S)", value=-50.0, step=0.5)
        lat_max = st.sidebar.number_input("Lat máxima (°S)", value=-20.0, step=0.5)

        if lon_min >= lon_max or lat_min >= lat_max:
            st.error("Revisa el dominio: lon_min < lon_max y lat_min < lat_max.")
            st.stop()

        domain = [lon_min, lon_max, lat_min, lat_max]

    # 🔁 Selector de modo
    modo_viz = st.radio(
        "Modo de visualización",
        ["Imagen única", "Animación (últimas 3 horas)"],
        horizontal=True,
    )

    # ============================
    # MODO 1: IMAGEN ÚNICA
    # ============================
    if modo_viz == "Imagen única":

        nc_path = descargar_goes_aws(
            fecha.year, doy, hora, banda, carpeta="data/GOES19"
        )

        if nc_path is None:
            st.error("No se encontró archivo GOES para esos parámetros.")
            st.stop()

        glm_path = None
        if mostrar_glm:
            glm_path = descargar_glm_aws(
                fecha.year,
                doy,
                hora,
                carpeta="data/GLM",
            )

        with st.spinner("Generando figura GOES..."):
            fig = plot_goes_band_chile(
                nc_path,
                domain=domain,
                region_name=region,
                glm_path=glm_path,
            )

        st.markdown(
            f"**Fecha:** {fecha} — **Día juliano:** {doy} — "
            f"**Hora UTC:** {hora:02d} — **Banda:** C{banda:02d}"
        )

        st.pyplot(fig)

        

        # ============================
    # MODO 2: ANIMACIÓN (última hora)
    # ============================
    else:
        # Descargamos TODOS los frames disponibles en la última hora
        frames = descargar_goes_ultima_hora_aws(
            fecha.year,
            doy,
            hora_central=hora,
            band=banda,
            carpeta="data/GOES19",
        )

        if not frames:
            st.warning(
                "No se encontraron imágenes GOES en la última hora "
                f"para las {hora:02d} UTC."
            )
            st.stop()

        n_frames = len(frames)

        # Estados en session_state
        if "frame_index" not in st.session_state:
            st.session_state.frame_index = n_frames - 1  # último frame por defecto

        if "playing" not in st.session_state:
            st.session_state.playing = False

        if "anim_speed" not in st.session_state:
            st.session_state.anim_speed = 0.5  # segundos entre frames

        # Caso especial: solo un frame → no tiene sentido animar
        if n_frames == 1:
            dt_sel, nc_sel = frames[0]
            etiqueta_sel = dt_sel.strftime("%H:%M")
            st.info(
                f"Solo se encontró una imagen disponible: {etiqueta_sel} UTC"
            )
            labels = None

        else:
            # Etiquetas con hora y minuto
            labels = [dt.strftime("%H:%M") for dt, _ in frames]

            col_play, col_speed = st.columns([1, 3])

            with col_play:
                if st.button("▶ / ⏸ Play / Pausa"):
                    st.session_state.playing = not st.session_state.playing

            with col_speed:
                st.session_state.anim_speed = st.slider(
                    "Velocidad (segundos entre frames)",
                    min_value=0.1,
                    max_value=2.0,
                    value=st.session_state.anim_speed,
                    step=0.1,
                )

            # Slider manual (sin key, usamos frame_index solo en session_state)
            idx = st.slider(
                "Frame de la animación (hora UTC)",
                min_value=0,
                max_value=n_frames - 1,
                value=st.session_state.frame_index,
                format="%d",
            )

            # Si el usuario movió el slider, actualizamos frame_index y pausamos
            if idx != st.session_state.frame_index:
                st.session_state.frame_index = idx
                st.session_state.playing = False

            # Frame seleccionado final
            dt_sel, nc_sel = frames[st.session_state.frame_index]
            etiqueta_sel = dt_sel.strftime("%H:%M")

        # ============================================
        # DESCARGA GLM (OPCIONAL)
        # ============================================
        glm_path = None
        if mostrar_glm:
            # Usamos la HORA del frame seleccionado para GLM
            h_glm = dt_sel.hour
            glm_path = descargar_glm_aws(
                fecha.year,
                doy,
                h_glm,
                carpeta="data/GLM",
            )

        # ============================================
        # PLOT
        # ============================================
        with st.spinner(
            f"Generando figura GOES para las {etiqueta_sel} UTC..."
        ):
            fig = plot_goes_band_chile(
                nc_sel,
                domain=domain,
                region_name=region,
                glm_path=glm_path,
            )

        st.pyplot(fig)

        # Texto informativo
        if n_frames == 1:
            st.markdown(
                f"Mostrando imagen única para las **{etiqueta_sel} UTC** "
                f"— Banda C{banda:02d}"
            )
        else:
            st.markdown(
                f"Mostrando animación con datos entre las "
                f"**{labels[0]}** y **{labels[-1]}** (UTC).  \n"
                f"Frame actual: **{etiqueta_sel} UTC** — Banda C{banda:02d}"
            )

        # ============================================
        # AVANZAR AUTOMÁTICAMENTE SI ESTÁ EN PLAY
        # ============================================
        if n_frames > 1 and st.session_state.playing:
            import time

            time.sleep(st.session_state.anim_speed)

            frame_idx = st.session_state.frame_index
            st.session_state.frame_index = (frame_idx + 1) % n_frames

            st.rerun()
    


# ---------------------------
# TAB 2: ESTACIONES (DEMO)
# ---------------------------

with tab_est:
    st.subheader("Serie temporal de estaciones (demo)")

    est_sel = st.selectbox("Estación", estaciones)

    df_filtrada = df_est[df_est["estacion"] == est_sel]

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Temperatura (°C)**")
        st.line_chart(df_filtrada.set_index("fecha")["temp"])

        st.markdown("**Viento (m/s)**")
        st.line_chart(df_filtrada.set_index("fecha")["viento"])

    with col2:
        st.markdown("**Precipitación (mm)**")
        st.bar_chart(df_filtrada.set_index("fecha")["pp"])

        st.markdown("**Datos crudos (demo)**")
        st.dataframe(df_filtrada, use_container_width=True)

    st.markdown(
        "> Más adelante puedes reemplazar este dataset por tus datos reales (CR2, DGA, estaciones propias, etc.)."
    )

# ---------------------------
# TAB 3: RESUMEN
# ---------------------------

with tab_resumen:
    st.subheader("Resumen operacional (demo)")

    st.markdown(
        """
        Aquí puedes construir un **relato operativo** para tus informes o LinkedIn:

        - Integración de GOES-19, ERA5 y estaciones.
        - Análisis de la nubosidad y sistemas frontales que afectan a Chile.
        - Evaluación cualitativa del impacto en precipitación y viento.
        - Comentarios sobre la configuración sinóptica (200 hPa, 500 hPa, superficie).
        """
    )

    st.markdown("### Ejemplo de texto automático (demo)")
    st.write(
        f"Entre el {fecha_inicio} y el {fecha_fin}, se monitorearon condiciones en la región **{region}**, "
        f"con foco en la variable **{variable_principal}**. El dashboard integra imágenes satelitales GOES-19, "
        "series de estaciones y campos de gran escala para apoyar la toma de decisiones operacionales."
    )

    st.markdown("---")
    st.markdown(
        "En el futuro podemos agregar un botón para **exportar este resumen a PDF**, incluyendo figuras clave y conclusiones."
    )


