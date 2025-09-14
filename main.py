import os
import discord
import asyncio
import ccxt
import pandas as pd
import ta
from dotenv import load_dotenv
from discord import app_commands

# Carrega credenciais
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
USER_ID = int(os.getenv("USER_ID"))
GUILD_ID = int(os.getenv("GUILD_ID"))  # ID do servidor onde o slash command vai aparecer
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))  # ID do canal onde quer enviar alertas

# Configura Discord
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Configura Binance via CCXT
exchange = ccxt.binance()
ativos = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'BNB/USDT:USDT', 'SOL/USDT:USDT', 'ENA/USDT:USDT', 'BERA/USDT:USDT', 'LINK/USDT:USDT', 'UNI/USDT:USDT',
          'AVAX/USDT:USDT', 'AAVE/USDT:USDT', 'SUI/USDT:USDT', 'PENDLE/USDT:USDT', 'HYPE/USDT:USDT']
timeframe = '15m'
limit = 100

RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

# ---------------- Monitoramento de indicadores ---------------- #
async def checar_ativo(symbol, user, channel):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp','open','high','low','close','volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        df['rsi'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi()
        bb = ta.volatility.BollingerBands(close=df['close'], window=20, window_dev=2)
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_lower'] = bb.bollinger_lband()
        df['bb_middle'] = bb.bollinger_mavg()

        ultima = df.iloc[-1]
        mensagem = None

        if ultima['rsi'] > RSI_OVERBOUGHT and ultima['close'] >= ultima['bb_upper']:
            mensagem = f"📉POSSÍVEL SHORT -> {symbol} RSI sobrecomprado: {ultima['rsi']:.2f} e fechou acima da banda superior: {ultima['close']:.2f} @here"
        elif ultima['rsi'] < RSI_OVERSOLD and ultima['close'] < ultima['bb_lower']:
            mensagem = f"📈POSSÍVEL LONG -> {symbol} RSI sobrevendido: {ultima['rsi']:.2f} e fechou abaixo da banda inferior: {ultima['close']:.2f} @here"

        if mensagem:
            await user.send(mensagem)
            await channel.send(mensagem)

    except Exception as e:
        print(f"Erro ao processar {symbol}: {e}")

async def monitor_indicadores():
    await client.wait_until_ready()
    user = await client.fetch_user(USER_ID)
    channel = client.get_channel(CHANNEL_ID)

    while not client.is_closed():
        await asyncio.gather(*(checar_ativo(symbol, user, channel) for symbol in ativos))
        await asyncio.sleep(900)

# ---------------- Comando /fetchprice ---------------- #
@tree.command(name="fetchprice", description="Retorna o preço atual de um ativo", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(symbol="Símbolo do ativo, ex: BTC/USDT")
async def fetchprice(interaction: discord.Interaction, symbol: str):
    try:
        ticker = exchange.fetch_ticker(symbol.upper())
        price = ticker['last']
        await interaction.response.send_message(f"💰 Preço atual de {symbol.upper()}: {price:.2f} USDT")
    except Exception as e:
        await interaction.response.send_message(f"❌ Não foi possível buscar o preço de {symbol.upper()}. Erro: {e}")

# ---------------- Eventos ---------------- #
@client.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=GUILD_ID))  # sincroniza comandos slash
    print(f"Bot conectado como {client.user}")

    # Envia "Oi" na DM e no canal do servidor
    try:
        user = await client.fetch_user(USER_ID)
        channel = client.get_channel(CHANNEL_ID)
        await user.send("WE UP! ÉUSGURI")
        await channel.send("WE UP! ÉUSGURI @here")
    except Exception as e:
        print(f"Erro ao enviar mensagem de teste: {e}")

    client.loop.create_task(monitor_indicadores())

client.run(TOKEN)
# ---------------- Fim do código ---------------- #