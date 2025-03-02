import discord
from discord.ext import commands
import os

def test():
    print(os.getcwd())

def run_bot():
    TOKEN = os.getenv('discord_token')
    AUDIO_PATH = f"{os.getcwd()}\\Songs\\"

    intents = discord.Intents.default()
    intents.message_content = True

    client = commands.Bot(command_prefix=".", intents=intents)


    @client.event
    async def on_ready():
        print(f"Bot {client.user} is running.")


    @client.command(name="join", aliases=["j"])
    async def join(ctx):
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await channel.connect()


    @client.command(name="play", aliases=["p"])
    async def play(ctx, filename: str):
        vc = ctx.voice_client
        
        if not vc:
            await ctx.send("Hey! I'm not there yet!")
        else:
            file_path = f"{AUDIO_PATH}\\{filename}"

            if os.path.exists(file_path):
                vc.stop()
                vc.play(discord.FFmpegPCMAudio(file_path))
            else:
                await ctx.send("Sorry, I don't have that in my songbook.")


    @client.command(name="disconnect", aliases=["d"])
    async def disconnect(ctx):
        await ctx.voice_client.disconnect()


    client.run(TOKEN)
