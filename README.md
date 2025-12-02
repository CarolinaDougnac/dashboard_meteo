🌩️ Dashboard Meteorológico Interactivo

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Framework-Streamlit-ff4b4b?logo=streamlit&logoColor=white)
![Cartopy](https://img.shields.io/badge/Geo-Cartopy-4b0082)
![Satellite](https://img.shields.io/badge/Satellite-GOES--19-0066cc)
![AWS Open Data](https://img.shields.io/badge/Data-AWS%20Open%20Data-FF9900?logo=amazon-aws&logoColor=white)
![Status](https://img.shields.io/badge/Status-v1.0-green)

GOES-19 + GLM + Animaciones | Streamlit | AWS S3 | Python

Este proyecto es un dashboard meteorológico interactivo desarrollado en Python + Streamlit, capaz de descargar, procesar y visualizar datos satelitales del GOES-19 directamente desde AWS S3, sin autenticación y en tiempo real.

Incluye soporte para animaciones, actividad eléctrica (GLM), paletas personalizadas, dominios configurables y un mini-mapa indicando el área graficada.

⸻

🚀 Funcionalidades principales

🛰️ 1. Visualización de GOES-19 (ABI L2 – CMIPF)
	•	Descarga automática desde AWS S3 (noaa-goes19)
	•	Soporta cualquier banda ABI: C02, C08, C13, etc.
	•	Paleta IR personalizada (colormap diseñada y ajustada a mano)
	•	Gráficos corregidos con coordenadas reales (Lat/Lon en borde externo)
	•	Zoom dinámico:
	•	Chile Continental
	•	Chile Central
	•	Isla de Pascua
	•	Dominio manual

⚡ 2. Actividad eléctrica (GLM)
	•	Descarga automática de archivos GLM L2 LCFA desde AWS
	•	Procesamiento de:
	•	Flashes
	•	Grupos
	•	Eventos
	•	Overlay sobre la imagen GOES con tamaño adaptativo según densidad
	•	Compatible con imagen única y animación

🎬 3. Animación de la última hora
	•	Frame cada ~10 minutos (todos los disponibles)
	•	Controles estilo reproductor:
	•	Play / Pausa
	•	Velocidad regulable
	•	Slider manual sincronizado
	•	Actualización dinámica en Streamlit usando st.session_state
	•	Soporte para GLM en cada frame

🗺️ 4. Mini-mapa del dominio
	•	Muestra el rectángulo exacto del área visualizada
	•	Incluye Sudamérica completa de referencia
	•	No tapa la imagen satelital

🧭 5. Ejes de latitud/longitud fuera del mapa
	•	Ejes externos alineados con la grilla
	•	Estilo limpio y profesional
	•	Formato en grados con símbolo °

🔧 6. Arquitectura modular

Código dividido en:
app.py               → Interfaz Streamlit
goes_plots.py        → Descarga, cargas .nc/.gml y graficado
custom_colormap.py   → Paleta IR personalizada

📸 Capturas

Guárdalas en /assets/ para que se vean en GitHub.

Imagen GOES C13 + GLM

📁 Estructura del repositorio
dashboard_meteo/
│
├── app.py
├── goes_plots.py
├── custom_colormap.py
│
├── requirements.txt
│
├── assets/
│   ├── screenshot_01.png
│   └── screenshot_anim.gif
│
└── data/
    ├── GOES19/
    ├── GLM/
    └── .gitignore

🔧 Instalación

1. Clonar el repositorio
git clone https://github.com/CarolinaDougnac/dashboard_meteo.git
cd dashboard_meteo

2. Instalar dependencias
pip install -r requirements.txt

▶️ Cómo ejecutar el dashboard
streamlit run app.py

🛰️ Datos utilizados

GOES-19 ABI (Cloud & Moisture Imagery – CMIPF)
	•	Fuente: AWS S3 Open Data
	•	Bucket: s3://noaa-goes19/
	•	Frecuencia: ~10 min
	•	Resolución: 0.5–2 km según banda
	•	Acceso libre, sin llaves ni credenciales

GLM (Geostationary Lightning Mapper)
	•	Fuente: noaa-goes19/GLM-L2-LCFA
	•	Flashes, grupos y eventos geolocalizados
	•	Frecuencia: 20 segundos



🛣️ Roadmap (v2, v3, v4…)

✔️ v1: GOES-19, GLM, dominios, animación, paletas
⬜ v2: Integración ERA5 / ERA5-Land
⬜ v3: Estaciones meteorológicas (CR2 / OGIMET / API propia)
⬜ v4: Calidad del aire (SO₂, PM10, PM2.5)
⬜ v5: Panel de modelos numéricos (WRF / GFS)
⬜ v6: Exportación a GIF / MP4 directamente desde Streamlit
⬜ v7: Hosting en Streamlit Cloud o Render

⸻

🤝 Contribuciones

Ideas, issues y PRs son bienvenidos.
Especialmente aportes para módulos ERA5 y Calidad del Aire.

⸻

👩‍🔬 Autora

Carolina Dougnac
Meteorología Operacional • Análisis Satelital • Machine Learning
🔗 https://www.linkedin.com/in/carolinadounac/
