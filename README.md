# 🔄 Sincronizador Google Sheets → Confluence

Este proyecto sincroniza automáticamente datos de Google Sheets a páginas de Confluence, preservando el formato (colores, negritas, alineación, celdas combinadas).

## 📋 Características

- ✅ Preserva formato de Google Sheets (colores, negritas, cursiva, subrayado)
- ✅ Maneja celdas combinadas (merge cells)
- ✅ Sincronización automática con GitHub Actions
- ✅ Soporte para múltiples hojas
- ✅ Actualización automática de páginas de Confluence

## 🚀 Configuración en GitHub

### 1. Crear el repositorio

```bash
# Inicializar repositorio
git init
git add .
git commit -m "Initial commit"

# Crear repositorio en GitHub y subir código
git branch -M main
git remote add origin https://github.com/TU-USUARIO/TU-REPO.git
git push -u origin main
```

### 2. Configurar Secrets en GitHub

Ve a tu repositorio → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Necesitas crear los siguientes secrets:

#### Secrets obligatorios:

| Secret | Descripción | Ejemplo |
|--------|-------------|---------|
| `CONFLUENCE_URL` | URL base de tu Confluence | `https://tuempresa.atlassian.net` |
| `CONFLUENCE_USER` | Tu email de Confluence | `tu-email@empresa.com` |
| `CONFLUENCE_API_TOKEN` | Token API de Confluence | Ver instrucciones abajo |
| `SPREADSHEET_ID` | ID de tu Google Sheet | `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms` |
| `GOOGLE_CREDENTIALS` | Credenciales de Service Account | Contenido completo del JSON |

#### Secrets para cada hoja:

Para cada hoja que quieras sincronizar, crea:

| Secret | Descripción | Ejemplo |
|--------|-------------|---------|
| `SHEET_1_NAME` | Nombre de la hoja en Google Sheets | `Dashboard Q4` |
| `SHEET_1_PAGE_ID` | ID de la página de Confluence | `123456789` |
| `SHEET_2_NAME` | Nombre de la segunda hoja | `Métricas` |
| `SHEET_2_PAGE_ID` | ID de la segunda página | `987654321` |

> 💡 **Nota:** El número de hojas es ilimitado, solo sigue el patrón `SHEET_N_NAME` y `SHEET_N_PAGE_ID`

### 3. Obtener credenciales

#### 📝 Token API de Confluence

1. Ve a: https://id.atlassian.com/manage-profile/security/api-tokens
2. Clic en **Create API token**
3. Dale un nombre (ej: "GitHub Actions Sync")
4. Copia el token (solo se muestra una vez)

#### 🔑 Credenciales de Google (Service Account)

1. Ve a: https://console.cloud.google.com/
2. Crea o selecciona un proyecto
3. Habilita la API de Google Sheets
4. Ve a **APIs & Services** → **Credentials**
5. Clic en **Create Credentials** → **Service Account**
6. Completa el formulario y crea la cuenta
7. Clic en la service account creada → **Keys** → **Add Key** → **Create new key**
8. Selecciona JSON y descarga el archivo
9. Copia **TODO el contenido del archivo JSON** al secret `GOOGLE_CREDENTIALS`

**Importante:** Comparte tu Google Sheet con el email de la service account (aparece en el JSON como `client_email`)

#### 🆔 Obtener IDs

**Spreadsheet ID:**
De la URL de tu Google Sheet:
```
https://docs.google.com/spreadsheets/d/aqui-va-el-id-de-tu-spreadsheet/edit
                                       ↑ Este es el SPREADSHEET_ID ↑
```

**Page ID de Confluence:**
De la URL de tu página de Confluence:
```
https://tuempresa.atlassian.net/wiki/spaces/TEAM/pages/123456789/
                                                               ↑ Este es el PAGE_ID ↑
```

## ⚙️ Configuración del workflow

El workflow se ejecuta automáticamente:
- **Cada 5 minutos** (puedes cambiar el horario en `.github/workflows/sync-sheets.yml`)
- **Manualmente** desde la pestaña Actions en GitHub

### Cambiar horario de ejecución

Edita el cron en `.github/workflows/sync-sheets.yml`:

```yaml
schedule:
  - cron: '0 8 * * *'  # Cada día a las 8 AM UTC
  # Ejemplos:
  # - cron: '0 */6 * * *'    # Cada 6 horas
  # - cron: '0 12 * * 1-5'   # Lunes a viernes al mediodía
  # - cron: '*/30 * * * *'   # Cada 30 minutos
```

## 🏃‍♂️ Ejecución manual

1. Ve a tu repositorio en GitHub
2. Clic en la pestaña **Actions**
3. Selecciona el workflow "Sync Google Sheets to Confluence"
4. Clic en **Run workflow** → **Run workflow**

## 🧪 Probar localmente

```bash
# Crear archivo .env
cat > .env << EOF
CONFLUENCE_URL=https://tuempresa.atlassian.net
CONFLUENCE_USER=tu-email@empresa.com
CONFLUENCE_API_TOKEN=tu-token
SPREADSHEET_ID=tu-spreadsheet-id
SHEET_1_NAME=Nombre de tu hoja
SHEET_1_PAGE_ID=id-de-la-pagina
EOF

# Copiar tus credenciales de Google
cp /ruta/a/tus/credenciales.json credentials.json

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar
python sync_metrics.py
```

## 📁 Estructura del proyecto

```
.
├── .github/
│   └── workflows/
│       └── sync-sheets.yml    # Workflow de GitHub Actions
├── scripts/
│   └── sync_metrics.py            # Script principal
├── requirements.txt           # Dependencias de Python
├── Dockerfile                 # (Opcional) Para Docker
├── .gitignore                 # Archivos a ignorar
└── README.md                  # Este archivo
```

## 🐳 Uso con Docker (Opcional)

```bash
# Construir imagen
docker build -t sheets-confluence-sync .

# Ejecutar
docker run --env-file .env sheets-confluence-sync
```

## 🔍 Solución de problemas

### Error: "No se encuentra el archivo credentials.json"
- Verifica que el secret `GOOGLE_CREDENTIALS` esté configurado
- Asegúrate de que el JSON esté completo y sea válido

### Error: "403 Forbidden" en Google Sheets
- Comparte el Google Sheet con el email de la service account
- El email está en el campo `client_email` del JSON de credenciales

### Error: "401 Unauthorized" en Confluence
- Verifica que el token de API sea correcto
- Verifica que el usuario tenga permisos para editar las páginas

### Las hojas no se encuentran
- Verifica que los nombres de las hojas (SHEET_N_NAME) coincidan exactamente
- Los nombres distinguen mayúsculas y minúsculas

## 👨‍💻 Autor

Gabriel Crespo para la materia de Aseguramiento de la Calidad de Software
