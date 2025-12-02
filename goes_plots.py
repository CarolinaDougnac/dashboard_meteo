from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.feature import NaturalEarthFeature
from cartopy.mpl.ticker import LatitudeFormatter, LongitudeFormatter
import cartopy.mpl.ticker as cticker
import GOES
import shutil
import s3fs
import matplotlib.colors as mcolors
import custom_color_palette as ccp
import os
import xarray as xr
import re
from datetime import datetime, timedelta
import matplotlib.ticker as mticker


# --- Colormap para C08 (WV 6.2 μm) ---
colors_c08 = [
    (0.4, 0.0, 0.0),
    (0.6, 0.2, 0.0),
    (0.8, 0.4, 0.0),
    (1.0, 0.6, 0.0),
    (1.0, 0.8, 0.0),
    (0.6, 0.8, 1.0),
    (0.2, 0.5, 1.0),
    (0.2, 0.2, 0.6)
]
cmap_c08 = mcolors.LinearSegmentedColormap.from_list("c08_goes", colors_c08)

# --- Colormap para C13 (IR 10.3 μm) ---
colors_c13 = [
    (0.5, 0.0, 0.0),
    (0.8, 0.2, 0.0),
    (1.0, 0.5, 0.0),
    (1.0, 0.8, 0.0),
    (0.5, 0.8, 1.0),
    (0.2, 0.4, 1.0),
    (0.6, 0.2, 0.8),
    (1.0, 0.0, 1.0)
]
cmap_c13 = mcolors.LinearSegmentedColormap.from_list("c13_goes", colors_c13)

# Carpeta donde guardamos los archivos NetCDF descargados
GOES_DIR = "data/GOES19"

# Filesystem anónimo para leer desde el bucket noaa-goes19 en AWS
fs = s3fs.S3FileSystem(anon=True)

# ---------------------------
# FUNCIONES AUXILIARES
# ---------------------------

# ======================================================
#   DESCARGA GOES
# ======================================================
def descargar_goes_aws(year: int, day_of_year: int, hour: int, band: int, carpeta: str = GOES_DIR) -> str | None:
    """
    Descarga un archivo GOES-19 ABI L2 CMIPF desde AWS (noaa-goes19) si no existe.

    year        : año (ej. 2024)
    day_of_year : día juliano (1–366)
    hour        : hora UTC (0–23)
    band        : banda ABI (2, 8, 13, etc.)
    carpeta     : carpeta local donde guardar el archivo

    Devuelve la ruta local al archivo .nc o None si no hay datos.
    """

    Path(carpeta).mkdir(parents=True, exist_ok=True)

    band_str = f"{band:02d}"

    # Prefijo de las llaves en el bucket S3:
    # noaa-goes19/ABI-L2-CMIPF/YYYY/DDD/HH/OR_ABI-L2-CMIPF-M6Cxx_G19_...
    prefix = (
        f"noaa-goes19/ABI-L2-CMIPF/"
        f"{year}/{day_of_year:03d}/{hour:02d}/"
        f"OR_ABI-L2-CMIPF-M6C{band_str}_G19_"
    )

    try:
        # Listar todos los archivos .nc que comiencen con ese prefijo
        keys = fs.glob(prefix + "*.nc")
    except Exception as e:
        print("Error listando S3:", e)
        return None

    if not keys:
        # No hay archivos para esa fecha/hora/banda
        return None

    # Nos quedamos con el primer archivo encontrado
    key = keys[0]

    nombre_local = Path(key).name
    ruta_local = Path(carpeta) / nombre_local

    # Si ya está descargado, devolvemos directo
    if ruta_local.exists():
        return str(ruta_local)

    # Descargar desde S3 a disco local
    try:
        with fs.open(key, "rb") as src, open(ruta_local, "wb") as dst:
            shutil.copyfileobj(src, dst)
    except Exception as e:
        print("Error descargando archivo desde S3:", e)
        return None

    return str(ruta_local)

def descargar_glm_aws(year: int, day_of_year: int, hour: int, carpeta: str = "data/GLM") -> str | None:
    """
    Descarga archivos GLM (actividad eléctrica) desde AWS.
    
    year        : año (YYYY)
    day_of_year : día juliano (1–366)
    hour        : hora UTC (0–23)
    carpeta     : carpeta local destino

    Devuelve la ruta local del archivo GLM o None.
    """
    Path(carpeta).mkdir(parents=True, exist_ok=True)

    # Prefijo GLM
    prefix = (
        f"noaa-goes19/GLM-L2-LCFA/"
        f"{year}/{day_of_year:03d}/{hour:02d}/"
        f"OR_GLM-L2-LCFA_G19_"
    )

    try:
        keys = fs.glob(prefix + "*.nc")
    except Exception as e:
        print("Error listando S3 GLM:", e)
        return None

    if not keys:
        return None

    # normal: tomar el primer archivo GLM encontrado
    key = keys[0]

    ruta_local = Path(carpeta) / Path(key).name

    # Si ya existe, devolverlo
    if ruta_local.exists():
        return str(ruta_local)

    # Descargar
    try:
        with fs.open(key, "rb") as src, open(ruta_local, "wb") as dst:
            shutil.copyfileobj(src, dst)
    except Exception as e:
        print("Error descargando GLM:", e)
        return None

    return str(ruta_local)

def descargar_goes_ultima_hora_aws(
    year: int,
    day_of_year: int,
    hora_central: int,
    band: int,
    carpeta: str = GOES_DIR,
):
    """
    Devuelve todos los frames disponibles en la última hora
    respecto a 'hora_central', con resolución nativa (~10 min).

    Retorna una lista de [(dt, ruta_local_nc), ...] ordenados por tiempo,
    donde dt es un datetime (UTC) reconstruido a partir del nombre del archivo.

    Ejemplo: si hora_central = 3 => intervalo [02:00, 03:00] UTC.
    """

    Path(carpeta).mkdir(parents=True, exist_ok=True)

    band_str = f"{band:02d}"

    # Vamos a mirar la hora central y la anterior
    horas_a_consultar = [hora_central - 1, hora_central]

    keys_todas = []

    for h in horas_a_consultar:
        if h < 0 or h > 23:
            # Para simplificar, ignoramos el cambio de día.
            continue

        prefix = (
            f"noaa-goes19/ABI-L2-CMIPF/"
            f"{year}/{day_of_year:03d}/{h:02d}/"
            f"OR_ABI-L2-CMIPF-M6C{band_str}_G19_"
        )

        try:
            ks = fs.glob(prefix + "*.nc")
            keys_todas.extend(ks)
        except Exception as e:
            print("Error listando S3 para animación 1h:", e)

    if not keys_todas:
        return []

    # Parsear tiempos desde el nombre del archivo
    frames_tmp = []  # (datetime, s3_key)

    for key in keys_todas:
        base = Path(key).name
        # Ejemplo: OR_ABI-L2-CMIPF-M6C13_G19_s20253350000208_e...
        # Buscamos la parte sYYYYDDDHHMM
        m = re.search(r"_s(\d{4})(\d{3})(\d{2})(\d{2})", base)
        if not m:
            continue

        yy = int(m.group(1))  # año
        jjj = int(m.group(2))  # día juliano
        hh = int(m.group(3))  # hora
        mm = int(m.group(4))  # minuto

        try:
            dt = datetime.strptime(f"{yy:04d} {jjj:03d} {hh:02d} {mm:02d}", "%Y %j %H %M")
        except Exception:
            continue

        frames_tmp.append((dt, key))

    if not frames_tmp:
        return []

    # Intervalo de la última hora respecto a hora_central
    # Nota: usamos year/day_of_year que vienen del filtro, asumimos mismo día.
    centro_dt = datetime.strptime(
        f"{year:04d} {day_of_year:03d} {hora_central:02d} 00",
        "%Y %j %H %M",
    )
    t_min = centro_dt - timedelta(hours=1)
    t_max = centro_dt  # inclusive

    frames_filtrados = [
        (dt, key)
        for dt, key in frames_tmp
        if t_min <= dt <= t_max
    ]

    # Ordenar por tiempo
    frames_filtrados.sort(key=lambda x: x[0])

    # Descargar a disco y devolver [(dt, ruta_local_nc), ...]
    frames = []

    for dt, key in frames_filtrados:
        nombre_local = Path(key).name
        ruta_local = Path(carpeta) / nombre_local

        if not ruta_local.exists():
            try:
                with fs.open(key, "rb") as src, open(ruta_local, "wb") as dst:
                    shutil.copyfileobj(src, dst)
            except Exception as e:
                print("Error descargando archivo para animación 1h:", e)
                continue

        frames.append((dt, str(ruta_local)))

    return frames

# ======================================================
#   PLOT GOES
# ======================================================
def plot_goes_band_chile(nc_path, domain=None, region_name="", glm_path=None):
    """
    Genera un gráfico del GOES-19 con:
    - Imagen satelital (CMI)
    - Zoom dinámico por dominios
    - Mapa pequeño con rectángulo del dominio (Opción A)
    """
    import custom_color_palette as ccp

    # ======================================================
    #   CARGAR ARCHIVO GOES
    # ======================================================
    ds = GOES.open_dataset(nc_path)

    # ======================================================
    #   DOMINIOS PREDEFINIDOS (lon_min, lon_max, lat_min, lat_max)
    # ======================================================
    dominios_predef = {
        "Chile Continental": [-85.0, -60.0, -60.0, -15.0],
        "Chile Central":     [-75.0, -67.0, -35.0, -30.0],
        "Isla de Pascua":    [-120.0, -103.0, -35.0, -20.0],
    }

    if domain is None:
        domain = dominios_predef.get(region_name, dominios_predef["Chile Continental"])

    lon_min, lon_max, lat_min, lat_max = domain

    # ======================================================
    #   LEER IMAGEN (CMI) + COORDENADAS
    #   (usamos lonlat="corner" para obtener Lon/Lat de vértices)
    # ======================================================
    # Si en algún momento necesitas detectar otra variable, aquí podrías
    # hacer un loop por ["CMI", "CMIP", "Rad", "Sectorized_CMI"].

    CMI, LonCor, LatCor = ds.image("CMI", lonlat="corner", domain=domain)

    sat      = ds.attribute("platform_ID")
    time_str = ds.attribute("time_coverage_start")
    band_id  = int(ds.variable("band_id").data[0])
    wl       = float(ds.variable("band_wavelength").data[0])

    long_name = CMI.long_name
    units     = CMI.units

    # ======================================================
    #   METADATOS PARA EL TÍTULO
    # ======================================================
    # Número de banda
    try:
        banda_num = int(ds.variable("band_id").data[0])
    except Exception:
        # Respaldo: intentar sacarlo del nombre del archivo
        import re  # o mejor: tener re importado arriba del archivo
        base = os.path.basename(nc_path)
        m = re.search(r"C(\d{2})_", base)
        banda_num = int(m.group(1)) if m else 0

    # Longitud de onda (si está disponible)
    try:
        wave = float(ds.variable("band_wavelength").data[0])
    except Exception:
        wave = None

    # Hora de inicio del barrido
    try:
        fecha_txt = ds.attribute("time_coverage_start")  # ej. "2025-12-01T00:00:20.8Z"
    except Exception:
        fecha_txt = ""


    

    # -------------------------------------------------
    # PALETAS ESPECÍFICAS POR BANDA (usando ccp)
    # -------------------------------------------------
    cmap  = None
    norm  = None
    bounds = None
    cbticks = None   # ticks de la barra de color

    # field = lo que realmente vamos a plotear (reflectancia o BT en °C)
    field = CMI.data.copy()
    cb_units = units  # etiqueta del colorbar

    if banda_num == 2:
        # Visible 0.64 µm — escala en grises (como en el notebook)
        paleta = [plt.cm.Greys_r, ccp.range(0.0, 1.0, 0.01)]
        cmap, ticks, norm, bounds = ccp.creates_palette([paleta], extend="both")
        cbticks = ccp.range(0.0, 1.0, 0.1)

    elif banda_num == 8:
        # Canal 8 (6.2 µm) — la paleta que usaste en el trabajo
        # Vapor de agua: trabajamos en °C (BT - 273.15)
        field = field - 273.15
        cb_units = "°C"

        paleta_1 = [['black',
                    (174/255, 46/255, 172/255),
                    (239/255, 139/255, 238/255)],
                    ccp.range( -90.0, -75.0, 0.5)]

#        paleta_2 = [[(0/255, 54/255, 250/255), 'lawngreen'],
        paleta_2 = [['darkgreen', 'lawngreen'],
                    ccp.range( -75.0, -60.0, 0.5)]

        paleta_3 = [['darkblue', 'white'],
                    ccp.range( -60.0, -45.0, 0.5)]

#        paleta_4 = [[(240/255, 240/255, 240/255),
#                    (60/255, 255/255, 60/255)],
        paleta_4 = [plt.cm.Greys,
                    ccp.range( -45.0, -25.0, 0.5)]

        paleta_5 = [[(65/255, 36/255, 25/255), 'orange',
                    'red', 'darkred', (63/255, 0/255, 0/255), 'black'],
                    ccp.range( -25.0,  0.0, 0.5)]

        cmap, ticks, norm, bounds = ccp.creates_palette(
            [paleta_1, paleta_2, paleta_3, paleta_4, paleta_5],
            extend="both"
        )
        cbticks = ccp.range(-90.0, 15.0, 15)

    elif banda_num == 13:
        # Canal 13 (10.3 µm) — paleta IR de tu notebook
        # IR ventana: también en °C
        field = field - 273.15
        cb_units = "°C"

        paleta_1 = [['maroon', 'red', 'darkorange',
                    '#ffff00', 'forestgreen', 'cyan', 'royalblue',
                    (148/255, 0/255, 211/255)],
                    ccp.range(-90.0, -30.0, 1.0)]

        paleta_2 = [plt.cm.Greys,
                    ccp.range(-30.0,  60.0, 1.0),
                    ccp.range(-90.0,  60.0, 1.0)]  # stretch/clip

        cmap, ticks, norm, bounds = ccp.creates_palette(
            [paleta_1, paleta_2],
            extend="both"
        )
        cbticks = ccp.range(-90.0, 60.0, 15)

    else:
        # Fallback para otras bandas: turbo autoescalado
        cmap = plt.cm.turbo
        norm = None
        bounds = None
        cbticks = None
        # Caso genérico
        vmin = float(np.nanmin(field))
        vmax = float(np.nanmax(field))
        paleta = [plt.cm.Greys, ccp.range(vmin, vmax, (vmax - vmin) / 20)]
        cmap, ticks, norm, bounds = ccp.creates_palette([paleta], extend="both")
        cbticks = ticks

    # ======================================================
    #   FIGURA CON DOS EJES (imagen + minimapa)
    # ======================================================
    fig = plt.figure(figsize=(10, 12))

    # ----- Eje principal (imagen satelital) -----
    ax = fig.add_axes([0.05, 0.32, 0.90, 0.63],
                           projection=ccrs.PlateCarree())
    
    #   EJES DE LATITUD / LONGITUD
    gl = ax.gridlines(
        draw_labels=True,
        linewidth=0.6,
        color="white",
        alpha=0.7,
        linestyle="--",
    )

    gl.top_labels = False
    gl.right_labels = False

    gl.xlabel_style = {"size": 10, "color": "white"}
    gl.ylabel_style = {"size": 10, "color": "white"}

    gl.xformatter = cticker.LongitudeFormatter(number_format='.1f')
    gl.yformatter = cticker.LatitudeFormatter(number_format='.1f')

    # Extensión al dominio elegido
    ax.set_extent([lon_min, lon_max, lat_min, lat_max],
                       crs=ccrs.PlateCarree())

    # Costas y fronteras
    ax.add_feature(cfeature.COASTLINE.with_scale("50m"),
                        edgecolor="yellow", linewidth=0.6)
    ax.add_feature(cfeature.BORDERS.with_scale("50m"),
                        edgecolor="yellow", linewidth=0.4)
    ax.add_feature(cfeature.LAND.with_scale("50m"),
                        facecolor="none", edgecolor="yellow", linewidth=0.2)


    proj_sat = ccrs.PlateCarree()
    im = ax.pcolormesh(
        LonCor.data,
        LatCor.data,
        field,
        cmap=cmap,
        norm=norm,
        transform=proj_sat
    )

    # ============================================
    #  EJES DE LATITUD / LONGITUD
    # ============================================
    # Elegimos un espaciado razonable según el dominio
    dx = max(1, int((lon_max - lon_min) / 6))  # aprox 6 divisiones en X
    dy = max(1, int((lat_max - lat_min) / 6))  # aprox 6 divisiones en Y

    xticks = np.arange(np.floor(lon_min), np.ceil(lon_max) + dx, dx)
    yticks = np.arange(np.floor(lat_min), np.ceil(lat_max) + dy, dy)

    # Ticks en proyección geográfica
    ax.set_xticks(xticks, crs=ccrs.PlateCarree())
    ax.set_yticks(yticks, crs=ccrs.PlateCarree())

    # Formateadores de grados
    lon_formatter = cticker.LongitudeFormatter(number_format=".0f", degree_symbol="°")
    lat_formatter = cticker.LatitudeFormatter(number_format=".0f", degree_symbol="°")

    ax.xaxis.set_major_formatter(lon_formatter)
    ax.yaxis.set_major_formatter(lat_formatter)

    # Estilo de las etiquetas
    ax.tick_params(
        axis="both",
        which="major",
        labelsize=8,
        colors="white",
        bottom=True,
        left=True,
        top=False,
        right=False,
    )

    # ======================================================
    #   FIGURA (imagen + minimapa)
    # ======================================================
    fig = plt.figure(figsize=(10, 12))

    # ----- Eje principal (imagen satelital) -----
    ax = fig.add_axes(
        [0.12, 0.25, 0.78, 0.70],  # posición afinada
        projection=ccrs.PlateCarree()
    )

    # Extensión al dominio elegido
    ax.set_extent([lon_min, lon_max, lat_min, lat_max],
                crs=ccrs.PlateCarree())

    # Costas y bordes
    ax.add_feature(cfeature.COASTLINE.with_scale("50m"),
                edgecolor="yellow", linewidth=0.6)
    ax.add_feature(cfeature.BORDERS.with_scale("50m"),
                edgecolor="yellow", linewidth=0.4)
    ax.add_feature(cfeature.LAND.with_scale("50m"),
                facecolor="none", edgecolor="yellow", linewidth=0.2)

    # Imagen satelital
    im = ax.pcolormesh(
        LonCor.data,
        LatCor.data,
        field,
        cmap=cmap,
        norm=norm,
        transform=ccrs.PlateCarree(),
    )

    # ======================================================
    #   GRIDLINES CON ETIQUETAS EXTERNAS (perfectamente alineadas)
    # ======================================================
    gl = ax.gridlines(
        draw_labels=True,
        linewidth=0.6,
        color="white",
        alpha=0.7,
        linestyle="--",
        crs=ccrs.PlateCarree(),
    )

    # Apagar etiquetas arriba y derecha
    gl.top_labels = False
    gl.right_labels = False

    # Ajustar estilo de etiquetas
    gl.xlabel_style = {"size": 9, "color": "black"}
    gl.ylabel_style = {"size": 9, "color": "black"}

    # Control fino de los ticks
    import matplotlib.ticker as mticker
    from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter

    dx = max(1, int((lon_max - lon_min) / 6))
    dy = max(1, int((lat_max - lat_min) / 6))

    gl.xlocator = mticker.MultipleLocator(dx)
    gl.ylocator = mticker.MultipleLocator(dy)

    gl.xformatter = LongitudeFormatter(number_format=".0f", degree_symbol="°")
    gl.yformatter = LatitudeFormatter(number_format=".0f", degree_symbol="°")

    # ======================================================
    #  OVERLAY DE ACTIVIDAD ELÉCTRICA (GLM)
    # ======================================================
    if glm_path is not None and os.path.exists(glm_path):
        try:
            ds_glm = xr.open_dataset(glm_path)

            # Buscamos variables de lat/lon que existan en el archivo
            lat_candidates = ["flash_lat", "event_lat", "group_lat", "latitude"]
            lon_candidates = ["flash_lon", "event_lon", "group_lon", "longitude"]

            lat_name = next(v for v in lat_candidates if v in ds_glm.variables)
            lon_name = next(v for v in lon_candidates if v in ds_glm.variables)

            lats = ds_glm[lat_name].values
            lons = ds_glm[lon_name].values

            # Filtrar por dominio
            mask = (
                (lons >= lon_min) & (lons <= lon_max) &
                (lats >= lat_min) & (lats <= lat_max)
            )
            lats = lats[mask]
            lons = lons[mask]

            # Si hay MUCHOS flashes, submuestrear un poco
            max_points = 5000
            if lats.size > max_points:
                idx = np.linspace(0, lats.size - 1, max_points, dtype=int)
                lats = lats[idx]
                lons = lons[idx]

            if lats.size > 0:
                ax.scatter(
                    lons,
                    lats,
                    s=8,
                    c="magenta",
                    marker=".",
                    alpha=0.7,
                    transform=ccrs.PlateCarree(),
                    zorder=6,
                    label="Flashes GLM",
                )
                # Pequeña leyenda
                ax.legend(
                    loc="lower left",
                    fontsize=8,
                    framealpha=0.4,
                )

        except Exception as e:
            # No rompemos el gráfico si falla GLM; solo lo avisamos en consola
            print(f"[WARN] No se pudo graficar GLM: {e}")


    # ======================================================
    #  BARRA DE COLORES (bien separada)
    # ======================================================

    # 👉 IMPORTANTE: elimina cualquier otro cax/colorbar que tuvieras antes
    # y usa solo este:
    cax = fig.add_axes([0.10, 0.12, 0.80, 0.03])  # más abajo que los ejes de lon/lat
    cb = plt.colorbar(im, cax=cax, orientation="horizontal", extend="both")
    cb.ax.tick_params(labelsize=8)

    # (opcional) título de la barra
    cb.set_label("ABI L2+ Cloud and Moisture Imagery brightness temperature (°C)",
                fontsize=8)

    # ======================================================
    #   MINIMAPA CON RECTÁNGULO DEL DOMINIO
    # ======================================================
    #ax_map = fig.add_axes([0.05, 0.05, 0.5, 0.15],
    ax_map = fig.add_axes([0.8, 0.76, 0.18, 0.18],  # (x, y, width, height) dentro de la figura
                          projection=ccrs.PlateCarree())

    ax_map.set_extent([-130, -30, -60, 20])  # vista amplia de Sudamérica
    ax_map.add_feature(cfeature.COASTLINE.with_scale("110m"))
    ax_map.add_feature(cfeature.BORDERS.with_scale("110m"))

    # Rectángulo del dominio seleccionado
    rect = plt.Rectangle(
        (lon_min, lat_min),
        lon_max - lon_min,
        lat_max - lat_min,
        fill=False,
        color="red",
        linewidth=1,
        transform=ccrs.PlateCarree()
    )
    ax_map.add_patch(rect)

    ax_map.set_title("Dominio seleccionado", fontsize=9)

    # ======================================================
    #   TÍTULO GENERAL
    # ======================================================
    if wave is not None:
        titulo_banda = f"G19 C{banda_num:02d} ({wave:.2f} µm)"
    else:
        titulo_banda = f"G19 C{banda_num:02d}"

    fig.suptitle(
        f"{titulo_banda}   {fecha_txt}   –   {region_name}",
        fontsize=20,
        fontweight="bold",
        y=0.97
    )

    return fig




# ======================================================
#   ANIMACION
# ======================================================

def descargar_goes_serie_aws(
    year: int,
    day_of_year: int,
    hora_central: int,
    n_horas: int,
    band: int,
    carpeta: str = GOES_DIR,
):
    """
    Devuelve una lista de frames para animación:
    [(hora_utc, ruta_local_nc), ...] ordenados cronológicamente.

    - year, day_of_year, band: igual que en descargar_goes_aws
    - hora_central : hora UTC seleccionada en el dashboard
    - n_horas      : número de horas hacia atrás (incluye la hora central)

    Solo incluye horas para las que se encontró archivo GOES.
    """
    horas = range(hora_central - (n_horas - 1), hora_central + 1)

    frames = []
    for h in horas:
        if h < 0 or h > 23:
            # fuera de rango, lo saltamos
            continue

        nc_path = descargar_goes_aws(
            year,
            day_of_year,
            h,
            band,
            carpeta=carpeta,
        )
        if nc_path is not None:
            frames.append((h, nc_path))

    # Ordenados por hora (por si acaso)
    frames.sort(key=lambda x: x[0])
    return frames