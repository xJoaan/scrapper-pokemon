import json
import os
import time
import requests
from playwright.sync_api import sync_playwright

CONFIG_FILE = "config.json"
PRODUCTS_FILE = "productos.json"

# Configuración de Twilio
TWILIO_ACCOUNT_SID = ""
TWILIO_AUTH_TOKEN = ""
TWILIO_FROM_NUMBER = ""
TWILIO_TO_NUMBER = ""

def enviar_sms(mensaje):
    """Envía un SMS con Twilio."""
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    
    data = {
        "To": TWILIO_TO_NUMBER,
        "From": TWILIO_FROM_NUMBER,
        "Body": mensaje
    }
    
    response = requests.post(url, data=data, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
    
    if response.status_code == 201:
        print("✅ SMS enviado con éxito.")
    else:
        print(f"⚠️ Error al enviar SMS: {response.text}")

def cargar_configuracion():
    """Carga la configuración de tiendas desde config.json."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def obtener_productos(tienda):
    """Scrapea los productos de una tienda específica según su configuración."""
    print(f"Scrapeando {tienda['nombre_tienda']}...")
    productos = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.goto(tienda["url"], timeout=60000)
        page.wait_for_load_state("networkidle")

        # Seleccionar productos con el selector correcto
        items = page.query_selector_all(tienda["selectores"]["producto"])

        for item in items:
            nombre_element = item.query_selector(tienda["selectores"]["nombre"])
            precio_element = item.query_selector(tienda["selectores"]["precio"])
            enlace_element = item.query_selector(tienda["selectores"]["enlace"])

            if nombre_element and enlace_element and precio_element:
                nombre = nombre_element.inner_text()
                enlace = enlace_element.get_attribute("href")
                precio = precio_element.inner_text()
                
                productos.append({
                    "nombre": nombre,
                    "enlace": enlace,
                    "precio": precio,
                    "tienda": tienda["nombre_tienda"]
                })

        browser.close()

    return productos

def cargar_productos_guardados():
    """Carga los productos desde productos.json si existe."""
    if os.path.exists(PRODUCTS_FILE):
        with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def guardar_productos(productos):
    """Guarda la lista de productos en productos.json."""
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump(productos, f, indent=4, ensure_ascii=False)

def verificar_nuevos_productos():
    print("🔍 Verificando nuevos productos en todas las tiendas...\n")
    
    tiendas = cargar_configuracion()
    productos_guardados = cargar_productos_guardados()
    
    productos_actuales = []
    for tienda in tiendas:
        productos_actuales.extend(obtener_productos(tienda))

    productos_guardados_nombres = {p["nombre"] for p in productos_guardados}
    nuevos_productos = [p for p in productos_actuales if p["nombre"] not in productos_guardados_nombres]
    
    if nuevos_productos:
        print("✅ Nuevos productos encontrados:")
        mensaje = "Nuevos productos:\n"
        for producto in nuevos_productos:
            mensaje += f"- [{producto['tienda']}] {producto['nombre']} - {producto['precio']} - {producto['enlace']}\n"

        # Enviar SMS
        enviar_sms(mensaje[:1600])  # Twilio tiene un límite de 1600 caracteres

        # Guardar los productos actualizados
        guardar_productos(productos_actuales)
    else:
        print("⚠️ No hay productos nuevos.")

# Bucle para ejecutarse cada 15 minutos
while True:
    verificar_nuevos_productos()
    print("\n⏳ Esperando 15 minutos para la siguiente verificación...\n")
    time.sleep(900)  # Espera 900 segundos (15 minutos)
