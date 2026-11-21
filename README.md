# `osa-epi`: Reproducible OMOP CDM Epidemiological Study of Obstructive Sleep Apnea Syndrome

[![CI - OSA Epidemiology Pipeline](https://github.com/ivanabregooo-web/osa_analysis/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ivanabregooo-web/osa_analysis/actions/workflows/ci.yml)

`osa-epi` is an end-to-end, containerized observational research pipeline built on the **OMOP Common Data Model (CDM)** and **PostgreSQL**

A continucacion se detallan las opciones para reproducir el analisis.

Opcion 1: Para correr el pipeline del analisis dentro de la carpeta raiz (ejemplo desde terminal cmd.exe), a manera local:

### 1. Crear ambiente de conda dedicado:
	> conda create -n osa-epi python=3.14 -y
	> conda activate osa-epi

### 2. Instalar el paquete en modo editable:
	> pip install -e ".[dev]" (Revisar nota abajo)

### 3. Correr el pipeline localmente:
Asegurarse de que la instancia de PostgreSQL OMOP CDM se alcanzable en 'DB_HOST:DB_PORT', luego correr:
	> run-osa-pipeline


Opcion 2 (recomendado): Utilizando servicio docker compose (ejemplo desde terminal cmd.exe):

### 1. Levantar el servicio multi-contenedor y correr el analisis
	> docker compose run --rm pipeline
Nota: *apendar `--build`—e.g., `docker compose run --rm --build pipeline`—cuando se modifiquen archivos en src/, sql/, o tests/*

### 2. Detener el servicio al finalizar:
	> docker compose down

Nota: es necesario contar un archivo .env en el folder raiz (ver .env.example)

Se implemento pytest y ruff check para asegurar el formateo, identacion y verificacion de pruebas.

Las dependencias utilizadas fueron congeladas en un archivo requirements.lock y especificadas dentro del pyproject.toml para asegurar la reproducibilidad.