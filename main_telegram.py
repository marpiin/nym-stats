# Actualización del archivo nym_scraper.py en el que se envían las recompensas a un bot de Telegram

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from datetime import datetime
import os
from telegram import Bot
import re
import asyncio
from dotenv import load_dotenv
import requests

load_dotenv()

# URL del nodo
URL = os.getenv("NYM_NODE_URL", "https://explorer.nym.spectredao.net/nodes/example")

# Cantidad bonded
BOND_AMOUNT = float(os.getenv("NYM_BOND_AMOUNT", "0"))

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

def get_fx_rate(from_currency="USD", to_currency="EUR"):
    """
    Get live FX rate using exchangerate-api v6 with API key from .env.
    Calls: https://v6.exchangerate-api.com/v6/<KEY>/latest/<FROM>
    Returns float rate (FROM -> TO) or None on failure.
    """
    key = os.getenv("EXCHANGE_RATE_API_KEY", "").strip()
    if not key:
        print("EXCHANGE_RATE_API_KEY not set in environment")
        return None

    url = f"https://v6.exchangerate-api.com/v6/{key}/latest/{from_currency}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("result") != "success":
            print(f"Exchange API returned non-success result: {data.get('result')}")
            return None
        rates = data.get("conversion_rates", {})
        rate = rates.get(to_currency)
        if rate is None:
            print(f"Currency {to_currency} not found in conversion_rates")
            return None
        return float(rate)
    except Exception as e:
        print(f"Failed to fetch FX rate {from_currency}->{to_currency}: {e}")
        return None

def monthly_values_in_fiat(df_monthly, token_price_usd, usd_to_eur=None):
    """
    Returns df with columns: month, reward_sum, value_usd, (optional) value_eur.
    """
    if token_price_usd is None or df_monthly is None or df_monthly.empty:
        return None

    df = df_monthly.copy()
    df["reward_sum"] = pd.to_numeric(df.get("reward_sum", pd.Series(dtype="float")), errors="coerce").fillna(0.0)
    df["value_usd"] = (df["reward_sum"] * float(token_price_usd)).round(8)
    if usd_to_eur:
        df["value_eur"] = (df["value_usd"] * float(usd_to_eur)).round(8)
    else:
        df["value_eur"] = pd.NA
    return df

def send_telegram_message(message):
    """
    Send a single HTML-formatted message to the Telegram bot.
    """
    bot = Bot(token=TELEGRAM_TOKEN)
    try:
        asyncio.run(bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="HTML"))
    except Exception as e:
        print(f"Failed to send telegram message: {e}")

def get_nym_token_price_selenium():
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)

    try:
        driver.get("https://explorer.nym.spectredao.net/dashboard")

        wait = WebDriverWait(driver, 15)
        price_element = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "p.text-xl.font-bold.text-white"))
        )
        price = price_element.text
    except Exception as e:
        driver.quit()
        raise RuntimeError(f"Failed to get NYM token price from page: {e}")
    driver.quit()
    return price

def parse_nym_price(text):
    """
    Parse a string like "$0.0532" or "Nym token price: $0.0532" and return float.
    Returns None if no numeric value found.
    """
    if not text:
        return None
    s = str(text).replace(",", "")  # remove thousand separators
    m = re.search(r"[-+]?\d*\.?\d+", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None

def get_stake_selenium():
    options = Options()
    # keep headless; adjust if using newer chrome versions (e.g. "--headless=new")
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    
    try:
        driver.get(URL)

        wait = WebDriverWait(driver, 15)
        stake_element = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "span.text-white.font-medium"))
        )
        stake = stake_element.text
    except Exception as e:
        driver.quit()
        raise RuntimeError(f"Failed to get stake from page: {e}")
    driver.quit()
    return stake

def stake_to_operator_rewards(stake):
    # soporte para recibir ya un número o una cadena como "1,234.56 NYM"
    if isinstance(stake, (int, float)):
        stake_value = float(stake)
    else:
        # extraer el primer número con coma/punto
        m = re.search(r"\d{1,3}[\d,]*(?:\.\d+)?", str(stake).replace("NYM", ""))
        if not m:
            raise ValueError(f"Could not parse stake value from '{stake}'")
        stake_str = m.group(0).replace(",", "")
        stake_value = float(stake_str)
    operator_rewards_value = stake_value - BOND_AMOUNT
    if operator_rewards_value < 0:
        operator_rewards_value = 0.0
    return round(operator_rewards_value, 8)

def save_to_csv(operator_rewards_value):
    today = datetime.now().strftime("%Y-%m-%d")
    filename = "nym_rewards_daily.csv"

    if os.path.exists(filename):
        try:
            df = pd.read_csv(filename)
        except Exception:
            df = pd.DataFrame(columns=["date", "operator_rewards_value"])
    else:
        df = pd.DataFrame(columns=["date", "operator_rewards_value"])

    new_row = pd.DataFrame({"date": [today], "operator_rewards_value": [operator_rewards_value]})
    if df.empty:
        df = new_row
    else:
        df = pd.concat([df, new_row], ignore_index=True)

    df.to_csv(filename, index=False)

def update_monthly_rewards():
    monthly_file = "nym_rewards_monthly.csv"
    today = datetime.now()
    current_month = today.strftime("%Y-%m")

    daily_file = "nym_rewards_daily.csv"
    # default diff 0 for safety
    diff = 0.0
    try:
        df_daily = pd.read_csv(daily_file)
        if "date" in df_daily.columns:
            df_daily["date"] = pd.to_datetime(df_daily["date"])
            df_daily = df_daily.sort_values("date")
        else:
            df_daily = pd.DataFrame(columns=["date", "operator_rewards_value"])
    except FileNotFoundError:
        df_daily = pd.DataFrame(columns=["date", "operator_rewards_value"])
    except Exception:
        df_daily = pd.DataFrame(columns=["date", "operator_rewards_value"])

    if len(df_daily) >= 2:
        last = df_daily.iloc[-1]
        prev = df_daily.iloc[-2]
        try:
            diff = float(last["operator_rewards_value"]) - float(prev["operator_rewards_value"])
            if diff < 0:
                diff = 0.0
        except Exception:
            diff = 0.0

    # Cargar o crear archivo mensual
    if os.path.exists(monthly_file):
        try:
            df_monthly = pd.read_csv(monthly_file)
        except Exception:
            df_monthly = pd.DataFrame({
                "month": pd.Series(dtype="str"),
                "reward_sum": pd.Series(dtype="float")
            })
    else:
        df_monthly = pd.DataFrame({
            "month": pd.Series(dtype="str"),
            "reward_sum": pd.Series(dtype="float")
        })

    # Actualizar mes actual
    if current_month in df_monthly["month"].values:
        df_monthly.loc[df_monthly["month"] == current_month, "reward_sum"] += diff
    else:
        new_row = pd.DataFrame({"month": [current_month], "reward_sum": [diff]})
        df_monthly = pd.concat([df_monthly, new_row], ignore_index=True)

    df_monthly.to_csv(monthly_file, index=False)

    # Retornar DataFrame y diff diario (nueva recompensa del día)
    return df_monthly, round(diff, 8)

if __name__ == "__main__":
    try:
        # Obtener stake y calcular recompensas diarias
        stake = get_stake_selenium()
        operator_rewards_value = stake_to_operator_rewards(stake)
        save_to_csv(operator_rewards_value)

        # Actualizar recompensas mensuales y obtener DataFrame + diff diario
        monthly_rewards, daily_new = update_monthly_rewards()

        if monthly_rewards is not None and not monthly_rewards.empty:
            monthly_text = "\n".join(
                [f"{row['month']}: {row['reward_sum']} NYM" for _, row in monthly_rewards.iterrows()]
            )
        else:
            monthly_text = "No monthly rewards yet."

        # Obtener precio del token y parsear a float
        token_str = get_nym_token_price_selenium()
        token_price_usd = parse_nym_price(token_str)

        # Obtener tipo de cambio USD->EUR (live)
        usd_to_eur = get_fx_rate("USD", "EUR")

        # Calcular valores mensuales en fiat si hay precio
        monthly_values = monthly_values_in_fiat(monthly_rewards, token_price_usd, usd_to_eur)

        # Preparar encabezado y cuerpo
        header = "<b>📢 Nym Operator Rewards Update</b>\n"
        header += f"<i>Date:</i> {datetime.now().strftime('%Y-%m-%d')}\n\n"

        body = []
        body.append(f"• Cumulative operator rewards: {operator_rewards_value:.6f} NYM")
        body.append(f"• New rewards today (delta): {daily_new:.6f} NYM")
        if token_price_usd is not None:
            if usd_to_eur is not None:
                token_price_eur = token_price_usd * usd_to_eur
                body.append(f"• NYM price: ${token_price_usd:.6f} USD / €{token_price_eur:.6f} EUR")
            else:
                body.append(f"• NYM price: ${token_price_usd:.6f} USD")
        else:
            body.append("• NYM price: unavailable")
        body_text = "\n".join(body)

        # Tabla monoespaciada dentro de <pre>
        table_lines = []
        if monthly_values is not None and not monthly_values.empty:
            # Header
            if usd_to_eur is not None:
                # Header
                table_lines.append(f"{'Month':<10}{'NYM':>12}{'USD ($)':>18}{'EUR (€)':>18}")
                table_lines.append("-" * 62)

                total_usd = 0.0
                total_eur = 0.0
                for _, row in monthly_values.iterrows():
                    month = row["month"]
                    nyms = float(row["reward_sum"])
                    usd = float(row["value_usd"])
                    eur_val = float(row["value_eur"]) if pd.notna(row["value_eur"]) else 0.0
                    total_usd += usd
                    total_eur += eur_val
                    table_lines.append(f"{month:<10}{nyms:12.6f}{usd:18.6f}{eur_val:18.6f}")

                table_lines.append("-" * 62)
                table_lines.append(f"{'Total (est.)':<10}{'':12}{total_usd:18.6f}{total_eur:18.6f}")
            else:
                table_lines.append(f"{'Month':<10}{'NYM':>18}{'USD (est)':>22}")
                table_lines.append("-" * 52)
                total_usd = 0.0
                for _, row in monthly_values.iterrows():
                    month = row["month"]
                    nyms = float(row["reward_sum"])
                    usd = float(row["value_usd"])
                    total_usd += usd
                    table_lines.append(f"{month:<10}{nyms:18.6f}{usd:22.6f}")
                table_lines.append("-" * 52)
                table_lines.append(f"{'Total (est.)':<10}{'':18}${total_usd:21.6f}")
        else:
            table_lines.append("No monthly rewards yet.")

        table_text = "<pre>" + "\n".join(table_lines) + "</pre>"

        note = "\n\n<i>Note:</i> daily delta is calculated from consecutive saved records. If there is no previous day record, delta = 0.0"

        full_message = header + body_text + "\n\n" + table_text + note

        # Enviar un único mensaje por Telegram
        send_telegram_message(full_message)

        print(f"{datetime.now()} - Saved operator rewards: {operator_rewards_value} (new: {daily_new})")

    except Exception as e:
        print(f"Error: {e}")