import os
import sys
import json
import requests
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

load_dotenv()

# --- Configuración ENVs ---
CONFLUENCE_URL = os.getenv("CONFLUENCE_URL")
CONFLUENCE_USER = os.getenv("CONFLUENCE_USER")
CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN")
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

# Validación
required_vars = [
    "CONFLUENCE_URL",
    "CONFLUENCE_USER",
    "CONFLUENCE_API_TOKEN",
    "SPREADSHEET_ID",
]
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    print(f"Error: Faltan variables de entorno: {', '.join(missing_vars)}")
    sys.exit(1)

if not os.path.exists(GOOGLE_CREDENTIALS_FILE):
    print(f"❌ Error: No se encuentra el archivo {GOOGLE_CREDENTIALS_FILE}")
    sys.exit(1)

# --- Configuración de hojas ---
sheets_config = []
i = 1
while True:
    sheet_name = os.getenv(f"SHEET_{i}_NAME")
    page_id = os.getenv(f"SHEET_{i}_PAGE_ID")

    if not sheet_name or not page_id:
        break

    sheets_config.append({"number": i, "name": sheet_name, "page_id": page_id})
    i += 1

if not sheets_config:
    print("Error: No se encontraron hojas configuradas")
    sys.exit(1)

print(f"Encontradas {len(sheets_config)} hojas configuradas\n")


def get_google_sheets_service():
    """Crea el servicio de Google Sheets API."""
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

    try:
        creds = Credentials.from_service_account_file(
            GOOGLE_CREDENTIALS_FILE, scopes=SCOPES
        )
        service = build("sheets", "v4", credentials=creds)
        return service
    except Exception as e:
        print(f"❌ Error creando servicio de Google Sheets: {e}")
        return None


def rgb_to_hex(color):
    """Convierte color RGB de Google Sheets a hexadecimal."""
    if not color:
        return None

    # Google Sheets devuelve colores en formato 0-1
    r = int(color.get("red", 0) * 255)
    g = int(color.get("green", 0) * 255)
    b = int(color.get("blue", 0) * 255)

    return f"#{r:02x}{g:02x}{b:02x}"


def read_sheet_with_format(service, spreadsheet_id, sheet_name):
    """Lee los datos Y el formato de una hoja específica, incluyendo celdas combinadas."""
    try:
        # Obtener el Sheet ID de la hoja
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = spreadsheet.get("sheets", [])

        sheet_id = None
        merges = []
        for sheet in sheets:
            if sheet.get("properties", {}).get("title") == sheet_name:
                sheet_id = sheet.get("properties", {}).get("sheetId")
                merges = sheet.get(
                    "merges", []
                )  # Obtener información de celdas combinadas
                break

        if sheet_id is None:
            print(f"❌ No se encontró la hoja '{sheet_name}'")
            return None, []

        # Leer datos con formato
        result = (
            service.spreadsheets()
            .get(
                spreadsheetId=spreadsheet_id, ranges=[sheet_name], includeGridData=True
            )
            .execute()
        )

        sheets_data = result.get("sheets", [])
        if not sheets_data:
            return None, []

        grid_data = sheets_data[0].get("data", [])[0]
        row_data = grid_data.get("rowData", [])

        # Procesar datos con formato
        formatted_rows = []
        for row in row_data:
            formatted_row = []
            values = row.get("values", [])

            for cell in values:
                cell_data = {
                    "value": cell.get("formattedValue", ""),
                    "backgroundColor": None,
                    "textColor": None,
                    "bold": False,
                    "italic": False,
                    "underline": False,
                    "horizontalAlignment": "LEFT",
                }

                # Obtener formato
                format_data = cell.get("effectiveFormat", {})

                # Color de fondo
                bg_color = format_data.get("backgroundColor")
                if bg_color:
                    cell_data["backgroundColor"] = rgb_to_hex(bg_color)

                # Color de texto
                text_format = format_data.get("textFormat", {})
                text_color = text_format.get("foregroundColor")
                if text_color:
                    cell_data["textColor"] = rgb_to_hex(text_color)

                # Negrita, cursiva, subrayado
                cell_data["bold"] = text_format.get("bold", False)
                cell_data["italic"] = text_format.get("italic", False)
                cell_data["underline"] = text_format.get("underline", False)

                # Alineación
                cell_data["horizontalAlignment"] = format_data.get(
                    "horizontalAlignment", "LEFT"
                )

                formatted_row.append(cell_data)

            formatted_rows.append(formatted_row)

        return formatted_rows, merges

    except Exception as e:
        print(f"❌ Error leyendo hoja '{sheet_name}': {e}")
        return None, []


def hex_to_confluence_color(hex_color):
    """Mapea un color hex a los colores predefinidos de Confluence."""
    if not hex_color:
        return None

    # Eliminar el #
    hex_color = hex_color.lstrip("#").lower()

    # Convertir a RGB
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
    except:
        return None

    # Mapear a colores de Confluence más cercanos
    # Confluence acepta: grey, blue, red, yellow, green, purple

    # Blanco o gris muy claro -> sin color
    if r > 240 and g > 240 and b > 240:
        return None

    # Gris
    if abs(r - g) < 30 and abs(g - b) < 30 and abs(r - b) < 30:
        if r < 180:
            return "grey"
        return None

    # Azul (más azul que rojo y verde)
    if b > r and b > g:
        return "blue"

    # Verde (más verde que rojo y azul)
    if g > r and g > b:
        return "green"

    # Rojo (más rojo que verde y azul)
    if r > g and r > b:
        return "red"

    # Amarillo (rojo + verde, poco azul)
    if r > 150 and g > 150 and b < 150:
        return "yellow"

    # Morado (rojo + azul, poco verde)
    if r > 100 and b > 100 and g < 150:
        return "purple"

    # Por defecto, sin color
    return None


def formatted_rows_to_confluence_table(formatted_rows, merges):
    """Convierte filas con formato en tabla de Confluence, manejando celdas combinadas."""
    import html

    if not formatted_rows:
        return "", 0

    # Determinar número de columnas
    num_cols = max(len(row) for row in formatted_rows if row)

    # Crear mapa de celdas combinadas
    # merge_map[row][col] = {'colspan': X, 'rowspan': Y, 'skip': False/True}
    merge_map = {}
    for merge in merges:
        start_row = merge.get("startRowIndex", 0)
        end_row = merge.get("endRowIndex", 0)
        start_col = merge.get("startColumnIndex", 0)
        end_col = merge.get("endColumnIndex", 0)

        colspan = end_col - start_col
        rowspan = end_row - start_row

        # La celda inicial lleva el colspan/rowspan
        if start_row not in merge_map:
            merge_map[start_row] = {}
        merge_map[start_row][start_col] = {
            "colspan": colspan,
            "rowspan": rowspan,
            "skip": False,
        }

        # Las demás celdas del merge se marcan como "skip"
        for r in range(start_row, end_row):
            if r not in merge_map:
                merge_map[r] = {}
            for c in range(start_col, end_col):
                if r == start_row and c == start_col:
                    continue  # Ya la procesamos arriba
                merge_map[r][c] = {"skip": True}

    # Usar formato de tabla de Confluence
    table_html = '<table data-layout="full-width"><colgroup>'
    for _ in range(num_cols):
        table_html += "<col />"
    table_html += "</colgroup><tbody>"

    # Procesar todas las filas
    data_rows = 0
    for row_idx, row in enumerate(formatted_rows):
        # Saltar filas completamente vacías
        if not any(cell.get("value", "").strip() for cell in row if cell):
            continue

        table_html += "<tr>"

        for col_idx in range(num_cols):
            # Verificar si esta celda debe saltarse (parte de un merge)
            if row_idx in merge_map and col_idx in merge_map[row_idx]:
                if merge_map[row_idx][col_idx].get("skip"):
                    continue  # Saltar esta celda, ya está incluida en otra

            cell = (
                row[col_idx]
                if col_idx < len(row)
                else {
                    "value": "",
                    "backgroundColor": None,
                    "textColor": None,
                    "bold": False,
                    "italic": False,
                    "underline": False,
                    "horizontalAlignment": "LEFT",
                }
            )

            bg_color_hex = cell.get("backgroundColor")
            text_color_hex = cell.get("textColor")

            # Convertir hex a color de Confluence
            confluence_color = hex_to_confluence_color(bg_color_hex)

            # Construir atributos de la celda
            td_attrs = []

            # Agregar colspan/rowspan si esta celda es inicio de un merge
            if row_idx in merge_map and col_idx in merge_map[row_idx]:
                merge_info = merge_map[row_idx][col_idx]
                if not merge_info.get("skip"):
                    if merge_info["colspan"] > 1:
                        td_attrs.append(f'colspan="{merge_info["colspan"]}"')
                    if merge_info["rowspan"] > 1:
                        td_attrs.append(f'rowspan="{merge_info["rowspan"]}"')

            # Color de fondo
            if confluence_color:
                td_attrs.append(f'data-highlight-colour="{confluence_color}"')

            attrs_str = " " + " ".join(td_attrs) if td_attrs else ""
            table_html += f"<td{attrs_str}>"

            # Contenido con formato
            safe_value = html.escape(str(cell.get("value", "")))

            # Aplicar formato de texto
            if cell.get("bold", False):
                safe_value = f"<strong>{safe_value}</strong>"
            if cell.get("italic", False):
                safe_value = f"<em>{safe_value}</em>"
            if cell.get("underline", False):
                safe_value = f"<u>{safe_value}</u>"

            # Color de texto
            text_confluence_color = hex_to_confluence_color(text_color_hex)
            if text_confluence_color:
                safe_value = (
                    f'<span style="color:{text_confluence_color}">{safe_value}</span>'
                )

            if not safe_value.strip():
                safe_value = "<br/>"

            table_html += f"<p>{safe_value}</p></td>"

        table_html += "</tr>"
        data_rows += 1

    table_html += "</tbody></table>"

    return table_html, data_rows


def get_page_info(page_id):
    """Obtiene la información de una página de Confluence."""
    url = (
        f"{CONFLUENCE_URL}/wiki/rest/api/content/{page_id}?expand=body.storage,version"
    )
    auth = (CONFLUENCE_USER, CONFLUENCE_API_TOKEN)

    try:
        response = requests.get(url, auth=auth)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error obteniendo página {page_id}: {e}")
        return None


def update_confluence_page(page_id, table_html, sheet_name):
    """Actualiza una página de Confluence con la tabla."""
    page_info = get_page_info(page_id)
    if not page_info:
        return False

    current_version = page_info["version"]["number"]
    page_title = page_info["title"]

    import datetime

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Contenido con mejor diseño
    page_content = f"""<ac:structured-macro ac:name="panel" ac:schema-version="1">
<ac:parameter ac:name="borderStyle">solid</ac:parameter>
<ac:parameter ac:name="borderColor">#4285f4</ac:parameter>
<ac:parameter ac:name="bgColor">#f8f9fa</ac:parameter>
<ac:rich-text-body>
<h1 style="color: #4285f4; margin: 0;">{sheet_name}</h1>
<p style="color: #666; margin: 5px 0 0 0;"><em>Última sincronización: {timestamp}</em></p>
</ac:rich-text-body>
</ac:structured-macro>

<p></p>

{table_html}

<p></p>

<ac:structured-macro ac:name="info" ac:schema-version="1">
<ac:rich-text-body>
<p><strong>Importada con un Script de Python</strong></p>
<p>Esta tabla es importada utilizando un script de python de google sheets con las API de Sheets y Confluence.</p>
</ac:rich-text-body>
</ac:structured-macro>"""

    url = f"{CONFLUENCE_URL}/wiki/rest/api/content/{page_id}"
    auth = (CONFLUENCE_USER, CONFLUENCE_API_TOKEN)
    headers = {"Content-Type": "application/json"}

    payload = {
        "version": {"number": current_version + 1},
        "title": page_title,
        "type": "page",
        "body": {"storage": {"value": page_content, "representation": "storage"}},
    }

    try:
        response = requests.put(url, json=payload, headers=headers, auth=auth)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Error actualizando página: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"Detalles: {e.response.text}")
        return False


# --- Proceso principal ---
print("=" * 80)
print("SINCRONIZACIÓN CON FORMATO PRESERVADO")
print("=" * 80)
print(f"Spreadsheet ID: {SPREADSHEET_ID}\n")

# Conectar con Google Sheets
service = get_google_sheets_service()
if not service:
    print("No se pudo conectar con Google Sheets API")
    sys.exit(1)

print("Conectado a Google Sheets API\n")

results = []

for sheet in sheets_config:
    print(f"\nProcesando: {sheet['name']}")
    print(f"Página Confluence: {sheet['page_id']}")

    # 1. Leer datos CON FORMATO de Google Sheets
    print("Leyendo datos y formato desde Google Sheets...")
    formatted_rows, merges = read_sheet_with_format(
        service, SPREADSHEET_ID, sheet["name"]
    )
    if not formatted_rows:
        print(f"No se pudieron leer los datos")
        results.append(
            {"sheet": sheet["name"], "success": False, "error": "No se leyeron datos"}
        )
        continue

    print(f"Leídas {len(formatted_rows)} filas con formato preservado")
    if merges:
        print(f"Detectadas {len(merges)} celdas combinadas")

    # 2. Convertir a tabla HTML con formato
    table_html, row_count = formatted_rows_to_confluence_table(formatted_rows, merges)
    if not table_html:
        print(f"No se pudo generar la tabla")
        results.append(
            {"sheet": sheet["name"], "success": False, "error": "Tabla vacía"}
        )
        continue

    print(f"Tabla generada: {row_count} filas de datos")

    # Mostrar muestra de colores detectados (primeras 3 filas)
    print(f"Muestra de colores detectados:")
    for i, row in enumerate(formatted_rows[:3]):
        if row:
            first_cell = row[0] if row else {}
            bg = first_cell.get("backgroundColor", "sin color")
            print(f"      Fila {i + 1}: fondo={bg}")

    # 3. Actualizar Confluence
    success = update_confluence_page(sheet["page_id"], table_html, sheet["name"])

    if success:
        print(f"Página actualizada exitosamente")
        print(f"Ver en: {CONFLUENCE_URL}/wiki/pages/{sheet['page_id']}")
        results.append({"sheet": sheet["name"], "success": True, "rows": row_count})
    else:
        print(f"Error al actualizar la página")
        results.append(
            {"sheet": sheet["name"], "success": False, "error": "Error al actualizar"}
        )

# --- Resumen final ---
print("\n" + "=" * 80)
print("RESUMEN DE SINCRONIZACIÓN")
print("=" * 80)

successful = sum(1 for r in results if r["success"])
print(f"\nExitosas: {successful}/{len(results)}")

if successful < len(results):
    print(f"Fallidas: {len(results) - successful}")
    print("\nDetalles de errores:")
    for r in results:
        if not r["success"]:
            print(f"   - {r['sheet']}: {r.get('error', 'Error desconocido')}")

print("\nFormato preservado: colores, negritas, alineación desde Google Sheets")
print("=" * 80)
sys.exit(0 if successful == len(results) else 1)
