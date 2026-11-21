- Poblacion:
Base de datos sintetica generada utilizando el motor Synthea. La base de datos original cosnta de 11,120 pacientes y fue convertida a un esquema OMOP CDM utlizando el plug-in Synthea-ETL. Revisar features.md para los detalles sobre la conversion a OMOP-CDM.

Se definio una cohorte de pacientes diagnosticados con Sindrome de Apnea Obstructiva del Sueño (SAOS), que consta de 358 pacientes sinteticos, extraida a partir de una base de datos mas grande. Nota: revisar features.md para los detalles sobre la base de datos.

Tabla 1 de la cohorte:

|Caracteristica|Valor|
|--------------|-----|
|Total patients(N)|358|
|Sex: FEMALE|100 (27.9%)|
|Sex: MALE|258 (72.1%)|
|Age at Index (years, median [q25-q75])|43.0 (37.0 - 50.0)|
|Baseline BMI (kg/m2, median [q25-q75])|29.1 (27.9 - 30.2)|
|Follow-up duration (days, median [q25-q75])|2309.0 (1576.3 - 4398.5)|


- Pregunta:
Caracterizacion epidemiologica de una cohorte de pacientes diagnosticados con SAOS durante su tratamiento continuo con terapia de CPAP (*Continous Positive Airway Pressure*).

Se respondieron las siguientes preguntas:

1. Distribucion de edad por sexo a la fecha indice
2. Distribucion de indice de masa corporal por sexo a la fecha indice
3. Las 10 comorbilidades mas frecuentes al evento indice
4. Persistencia de terapia con CPAP utilizando algoritmo *gaps and islands*
5. Probabilidad de supervivencia post-diagnostico de OSA.

- Metodo:

El analisis se containerizo dentro de un dockerfile para asegurar su reproducibilidad. Asi mismo, la base de datos utlizada es manejada, junto con el analisis, a traves de un servicio docker-compose. Tambien es posible correr el pipeline de manera local.

Los resultados del analisis son generados a manera de figuras dentro de la carpeta outputs/figures/