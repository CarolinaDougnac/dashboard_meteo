🌩️ Dashboard Meteorológico Interactivo — Versión 1

GOES-19 + GLM desde AWS S3 | Streamlit | Python

Este proyecto es un dashboard meteorológico interactivo desarrollado en Python + Streamlit, capaz de:
	•	📥 Descargar imágenes GOES-19 directamente desde AWS S3 (GOES ABI L2 Cloud & Moisture Imagery).
	•	⚡ Visualizar actividad eléctrica (GLM) superpuesta al infrarrojo.
	•	🎨 Aplicar una paleta de colores personalizada para temperatura de brillo IR.
	•	🎬 Animar la última hora disponible (imágenes cada ~10 min) con:
	•	Botón Play/Pausa
	•	Control de velocidad
	•	Slider manual sincronizado
	•	🌍 Dominios configurables: Chile continental, Chile central, Isla de Pascua o zoom manual.
	•	🗺️ Minimapa del dominio elegido
	•	🧭 Grilla geográfica con ejes externos de lat/lon alineados

🔧 Esta es la versión 1 (MVP). El proyecto seguirá creciendo con ERA5, estaciones meteorológicas y datos de calidad del aire.

📁 Estructura del proyecto

dashboard_meteo/
│
├── app.py                 # Aplicación principal Streamlit
├── goes_plots.py          # Funciones de descarga y graficación GOES-19/GLM
├── custom_colormap.py     # Paleta personalizada IR
│
├── data/                  # Espacio para descargas AWS (vacío en repo)
│   ├── GOES19/
│   ├── GLM/
│   └── .gitignore
│
├── assets/                # Screenshots para README
│
├── requirements.txt
│
└── README.md

🔧 Instalación

Requisitos:
	•	Python 3.10+
	•	pip o conda



