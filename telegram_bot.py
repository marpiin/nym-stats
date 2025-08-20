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

load_dotenv()

# URL del nodo
URL = os.getenv("NYM_NODE_URL", "https://explorer.nym.spectredao.net/nodes/example")

# Cantidad bonded
BOND_AMOUNT = float(os.getenv("NYM_BOND_AMOUNT", "0"))

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

def send_telegram_message(message):
    """
    Send a message to your Telegram bot (synchronous, with error handling)
    """
    bot = Bot(token=TELEGRAM_TOKEN)
    try:
        asyncio.run(bot.send_message(chat_id=CHAT_ID, text=message))
    except Exception as e:
        print(f"Failed to send telegram message: {e}")

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

        # Preparar texto de recompensas mensuales
        if monthly_rewards is not None and not monthly_rewards.empty:
            monthly_text = "\n".join(
                [f"{row['month']}: {row['reward_sum']} NYM" for _, row in monthly_rewards.iterrows()]
            )
        else:
            monthly_text = "No monthly rewards yet."

        # Construir mensaje (incluye recompensa diaria nueva)
        message = (
            f"Nym Operator Rewards Update\n"
            f"Date: {datetime.now().strftime('%Y-%m-%d')}\n"
            f"Today's cumulative operator rewards: {operator_rewards_value} NYM\n"
            f"Today's new rewards (delta): {daily_new} NYM\n\n"
            f"Monthly rewards so far:\n{monthly_text}"
        )

        # Enviar mensaje por Telegram
        send_telegram_message(message)

        print(f"{datetime.now()} - Saved operator rewards: {operator_rewards_value} (new: {daily_new})")

    except Exception as e:
        print(f"Error: {e}")