```
# Nym Rewards Scraper

Este proyecto contiene un script en Python para obtener las recompensas de un nodo de Nym y almacenarlas en ficheros CSV (diarios y mensuales).  
El script está pensado para ejecutarse automáticamente en una VM de Google Cloud utilizando **cron**.

## Estructura del proyecto

```

.
├── nym\_scraper.py          # Script principal que obtiene y guarda las recompensas
├── requirements.txt        # Dependencias necesarias
├── .gitignore              # Archivos y carpetas ignorados por git
└── README.md               # Documentación del proyecto

````

## Instalación

1. Clonar el repositorio:
   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd <NOMBRE_DEL_PROYECTO>
````

2. Crear y activar un entorno virtual (opcional pero recomendado):

   ```bash
   python3 -m venv venv
   source venv/bin/activate   # Linux/Mac
   venv\Scripts\activate      # Windows
   ```

3. Instalar dependencias:

   ```bash
   pip install -r requirements.txt
   ```

## Uso local

Ejecutar el script manualmente:

```bash
python nym_scraper.py
```

## Ejecución automática en VM con cron

En la VM, editar la crontab:

```bash
crontab -e
```

Ejemplo para ejecutar todos los días a las 12:00:

```bash
0 12 * * * /home/USUARIO/venv/bin/python /home/USUARIO/nym_scraper.py >> /home/USUARIO/log_nym.txt 2>&1
```

## Salida generada

* **nym\_rewards\_daily.csv** → Registro diario de recompensas del operador.
* **nym\_rewards\_monthly.csv** → Acumulado mensual de recompensas.

Estos archivos están excluidos del repositorio (`.gitignore`).

---

## Licencia

Este proyecto se distribuye bajo la licencia MIT.

```
```
