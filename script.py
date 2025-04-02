import json
import os
import time
import requests
import smtplib
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from playwright.sync_api import sync_playwright
from smtplib import SMTPAuthenticationError, SMTPConnectError, SMTPException

CONFIG_FILE = "config.json"
PRODUCTS_FILE = "productos.json"

# Configuración de Twilio (SMS)
TWILIO_ACCOUNT_SID = ""
TWILIO_AUTH_TOKEN = ""
TWILIO_FROM_NUMBER = ""
TWILIO_TO_NUMBER = ""

# Configuración de Email
EMAIL_FROM = "tu_email@gmail.com"
EMAIL_TO = "destinatario@gmail.com"
EMAIL_PASSWORD = "tu_contraseña_de_aplicación"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Configuración de Telegram
TELEGRAM_BOT_TOKEN = ""  # Ejemplo: "123456789:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
TELEGRAM_CHAT_ID = ""      # Ejemplo: "123456789"

def enviar_telegram(mensaje):
    """Envía un mensaje a través de Telegram."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": mensaje,
            "parse_mode": "HTML"
        }
        
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        print("✅ Mensaje enviado a Telegram con éxito.")
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error al enviar mensaje a Telegram: {str(e)}")

def enviar_email(asunto, mensaje):
    """Envía un correo electrónico con los nuevos productos con manejo robusto de errores."""
    try:
        # Crear el mensaje
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO
        msg['Subject'] = asunto
        
        # Cuerpo del mensaje
        msg.attach(MIMEText(mensaje, 'plain'))
        
        # Intentar enviar el correo con manejo de errores específicos
        try:
            print("🔌 Conectando al servidor SMTP de Gmail...")
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                
                print("🔑 Autenticando...")
                server.login(EMAIL_FROM, EMAIL_PASSWORD)
                
                print("📤 Enviando correo...")
                server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
                print("✅ Correo electrónico enviado con éxito.")
                
        except SMTPAuthenticationError:
            print("⚠️ Error de autenticación: Usuario o contraseña incorrectos.")
            print("ℹ️ Asegúrate de usar una 'Contraseña de aplicación' si tienes 2FA activado.")
        except SMTPConnectError:
            print("⚠️ Error de conexión: No se pudo conectar al servidor SMTP.")
            print("ℹ️ Verifica tu conexión a internet y los parámetros del servidor SMTP.")
        except socket.timeout:
            print("⚠️ Tiempo de espera agotado: El servidor no respondió a tiempo.")
        except smtplib.SMTPSenderRefused:
            print("⚠️ El servidor rechazó al remitente. Verifica EMAIL_FROM.")
        except smtplib.SMTPRecipientsRefused:
            print("⚠️ El servidor rechazó al destinatario. Verifica EMAIL_TO.")
        except smtplib.SMTPDataError:
            print("⚠️ Error de datos: El servidor rechazó el contenido del mensaje.")
            print("ℹ️ Puede ser por mensaje demasiado largo o contenido no permitido.")
        except Exception as e:
            print(f"⚠️ Error inesperado al enviar correo: {str(e)}")
            
    except Exception as e:
        print(f"⚠️ Error general al preparar el correo: {str(e)}")

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
                
                # 🔹 SOLO modificar los enlaces si la tienda es Cardzone
                if tienda["nombre_tienda"].lower() == "cardzone" and enlace:
                    if not enlace.startswith("http"):  
                        enlace = f"https://cardzone.es{enlace}"  # Agregar prefijo si falta
                
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
        
        # Mensaje para SMS/Email (texto plano)
        mensaje_sms_email = "Nuevos productos:\n"
        for producto in nuevos_productos:
            mensaje_sms_email += f"- [{producto['tienda']}] {producto['nombre']} - {producto['precio']} - {producto['enlace']}\n"

        # Mensaje para Telegram (formato HTML) - ESTE ES EL BLOQUE QUE PREGUNTAS
        mensaje_telegram = "🚨 <b>NUEVOS PRODUCTOS ENCONTRADOS</b> 🚨\n\n"
        for prod in nuevos_productos:
            mensaje_telegram += f"""
🛍️ <b>{prod['tienda']}</b>
📌 {prod['nombre']}
💰 <i>{prod['precio']}</i>
🔗 <a href="{prod['enlace']}">Ver producto</a>
------------------------
"""
        # Enviar notificaciones por todos los canales
        enviar_sms(mensaje_sms_email[:1600])  # SMS con límite de caracteres
        enviar_email("🚨 Nuevos productos encontrados!", mensaje_sms_email)
        enviar_telegram(mensaje_telegram)  # Telegram con formato HTML

        # Guardar los productos actualizados
        guardar_productos(productos_actuales)
    else:
        print("⚠️ No hay productos nuevos.")

# Bucle para ejecutarse cada 15 minutos
while True:
    verificar_nuevos_productos()
    print("\n⏳ Esperando 15 minutos para la siguiente verificación...\n")
    time.sleep(900)  # Espera 900 segundos (15 minutos)
