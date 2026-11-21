La base de datos original consta de 11,120 pacientes sinteticos, generados con el motor Synthea.

Pasos para la generacion:

Se recomienda trabajar con un administrador de entornos (e.g. Anaconda navigator). Es necesario contar con Java Development Kit (JDK) 17+.

Ejemplo de instalación:

conda install -c conda-forge openjdk=25.0.2

Confirmar que se se cuenta con JDK 17+ mediante:

java --version

También es necesario contar con Git para clonar el repositorio de Synthea:

git clone https://github.com/synthetichealth/synthea.git

Una vez clonado, buscar el archivo synthea/src/main/resources/synthea.properties y modificar las siguientes lineas:

exporter.fhir.export = false
exporter.csv.export = true
physiology.generator.enabled = true
exporter.metadata.export = false
exporter.hospital.fhir.export = false
exporter.symptoms.csv.export = true
exporter.symptoms.text.export = true
exporter.symptoms.mode = 1
Finalmente correr el generador:

	> .\gradlew.bat run -Dorg.gradle.jvmargs="-Xmx8g" --args="p 10000 -t 1"

Posteriormente, la base de datos fue convertida a un esquema OMOP-CDM, mediante ETL-Synthea.
A continucación se documentan los pasos de la conversión:

- Clonar repositorio de ETL-Synthea (terminal):
	>  git clone https://github.com/OHDSI/ETL-Synthea.git

- Descargar archivo .zip de tablas de OMOP, en especifico version 5.4.2:
	> https://github.com/OHDSI/CommonDataModel/releases#release-v5.4.2

- Montar postgres con docker usando bind mount (terminal):
	> docker run --rm --name my_postgres --env-file .env -p 5432:5432 -v "%cd%:/workspace" -v "C:\Users\IVAN\Documents\postgres_data:/var/lib/postgresql/data" -d postgres:15.4

- Preparar archivos de sql OMOPCDM_postgresql_5.4_constraints.sql, OMOPCDM_postgresql_5.4_ddl.sql, OMOPCDM_postgresql_5.4_primary_keys.sql, OMOPCDM_postgresql_5.4_indices.sql (editor de texto):
	> buscar '@cdmDatabaseSchema' e intercambiar por 'public'

- Ejecutar el script DDL para crear tablas vacias (terminal):
	> docker exec my_postgres psql -U postgres -d postgres -f "workspace/omop_cdm_postgresql/OMOPCDM_postgresql_5.4_ddl.sql"

- Crear esquema nativo (terminal):
	> docker exec my_postgres psql -U postgres -d postgres -f "/workspace/ETL-Synthea/inst/sql/sql_server/synthea_version/v330/create_synthea_tables.sql"

- LLenar tablas vacias con los datos de synthea usando el script de cargado propio (terminal):
	> docker exec my_postgres psql -U postgres -d postgres -f "/workspace/load_synthea.sql"
	nota: se copiaron la mayoria de los archivos pero fallo casi al final, aca debuggeo ese error y copio los archivos faltantes:

- Debuggear: Mi version de synthea genero 1 columna 'NPI' en providers.csv y organizations.csv que las tablas vacias no estaban contemplando, asi que tuve que agregarlas manualmente (terminal):
	> docker exec my_postgres psql -U postgres -d postgres -c "ALTER TABLE native.organizations ADD COLUMN npi VARCHAR(255); ALTER TABLE native.providers ADD COLUMN npi VARCHAR(255);"

- Copiar archivos faltantes (terminal):
	> docker exec my_postgres psql -U postgres -d postgres -c "COPY native.providers FROM '/workspace/data/providers.csv' WITH (FORMAT CSV, HEADER); COPY native.organizations FROM '/workspace/data/organizations.csv' WITH (FORMAT CSV, HEADER);"

- Cargar vocabularios: se creo un script para copiar los archivos .csv de vocabualarios de OMOP (terminal):
	> docker exec my_postgres psql -U postgres -d postgres -f "/workspace/load_vocab.sql"
	nota: en este script se tuvo que especificar el delimitador como tab en vez de coma, porque si no se rompia.

- Identificar las llaves primarias (terminal):
	> docker exec my_postgres psql -U postgres -d postgres -f "/workspace/omop_cdm_postgresql/OMOPCDM_postgresql_5.4_primary_keys.sql"

- Crear los indices (terminal):
	> docker exec my_postgres psql -U postgres -d postgres -f "/workspace/omop_cdm_postgresql/OMOPCDM_postgresql_5.4_indices.sql"

- Preparar archivos de ETL-Synthea/inst/sql/sql_server/cdm_version/v540 (notepad++):
	> en todo el directorio, buscar '@cdm.schema' y reemplazar por 'public' y reemplazar '@synthea.schema' por 'native'

- Preparar ambiente en *RStudio* para correr el ETL:
	> install.packages("remotes")
	> remotes::install_github("OHDSI/DatabaseConnector")
	> library(DatabaseConnector)
	nota: en este punto me encontre un error:
Error: package or namespace load failed for ‘DatabaseConnector’:
.onLoad falló en loadNamespace() para 'rJava', detalles:
llamada: fun(libname, pkgname)
error: JAVA_HOME cannot be determined from the Registry
Para solucionarlo, tuve que instalar java (https://adoptium.net/en-GB), version JDK 25 LTS, windows, x64.
	> library(DatabaseConnector)
	> library(ETLSyntheaBuilder)
	drivers para comunicacion R-Docker:
	> downloadJdbcDrivers("postgresql", pathToDriver = getwd())
	conectar con base de datos:
	> cd <- createConnectionDetails(
            dbms = "postgresql",
            server = "localhost/postgres",
            user = "postgres",
            password = "password", 
            port = 5432,
            pathToDriver = getwd()
            )
	nota: en este punto RStudio se atoraba con este error:
	Running: insert_visit_occurrence.sql
	| | 0%Error in `.createErrorReport()`:! Error executing SQL: org.postgresql.util.PSQLException: ERROR: relation "public.all_visits" does not exist
	Position: 1185
	Me estaba haciendo falta pre construir una tabla temporal que ayuda a pasar encuentros continuos de synthea como una sola visita de larga duracion.
	construir tabla de visitas:
	> CreateVisitRollupTables(
			connectionDetails = cd,
			cdmSchema = "public",
			syntheaSchema = "native",
			cdmVersion = "5.4"
			)
	Transformar datos de eventos synthea a esquema omop (este paso tardo 66 minutos) :
	> LoadEventTables(
		connectionDetails = cd,
	    cdmSchema = "public",
	    syntheaSchema = "native",
	    cdmVersion = "5.4",
	    syntheaVersion = "3.3.0"
	    )
	Finalmente, correr script para aplicar mapeo de llaves foraneas (terminal):
	> docker exec my_postgres psql -U postgres -d postgres -f "/workspace/omop_cdm_postgresql/OMOPCDM_postgresql_5.4_constraints.sql"


Conteo de filas por tablas:

| table_name | row_count |
|------------|-----------|
| measurement | 5875466 |
| observation | 3059641|
| cost | 1740419 |
| procedure_occurrence | 1015698 |
| drug_exposure | 697826 |
| visit_occurrence | 604979 |
| condition_occurrence | 190298 |
| condition_era | 187352 |
| drug_era | 127947 |
| person | 11122 |