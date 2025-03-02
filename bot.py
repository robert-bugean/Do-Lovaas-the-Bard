import os
import discord
from discord.ext import commands


TOKEN = os.getenv('discord_token')
AUDIO_PATH = f"{os.getcwd()}\\Songbook\\"

intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix=".", intents=intents)

loop = False
current_song = None


def run_bot():
    @client.event
    async def on_ready():
        print(f"Bot {client.user} is running.")

    # JOIN
    @client.command(name="join", aliases=["j"])
    async def join(ctx):
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await channel.connect()

    # PLAY
    @client.command(name="play", aliases=["p"])
    async def play(ctx, file_name: str):
        global current_song
        vc = ctx.voice_client
        
        if not vc:
            await ctx.send("Hey! I'm not there yet!")
        else:
            file_path = f"{AUDIO_PATH}\\{file_name}"

            if os.path.exists(file_path):
                current_song = file_path
                vc.stop()
                play_audio(vc, file_path, ctx)
                await show_controls(ctx)
            else:
                await ctx.send("Sorry, I don't have that in my songbook.")

    def play_audio(vc, file_path, ctx):
        vc.play(
            discord.FFmpegPCMAudio(file_path),
            after=lambda e: check_loop(vc, ctx)
        )

    def check_loop(vc, ctx):
        if loop:
            play_audio(vc, current_song, ctx)

    # PAUSE
    @client.command(name="pause")
    async def pause(ctx):
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()
        else:
            await ctx.send("I'm not playing anything.")

    # RESUME 
    @client.command(name="resume")
    async def resume(ctx):
        if not ctx.voice_client.is_playing():
            ctx.voice_client.resume()

    # STOP
    @client.command(name="stop", aliases=["s"])
    async def stop(ctx):
        await ctx.voice_client.disconnect()

    # LOOP
    @client.command(name="loop", aliases=["l"])
    async def toggle_loop(ctx):
        global loop
        loop = not loop

        await ctx.send(f"Loop: {loop}.")


    async def show_controls(ctx):
        with open("icon.png", "rb") as icon_file:
            icon = discord.File(icon_file, filename="icon.png")

        embed = discord.Embed(
            title="TITLE",
            color=discord.Color.red()
        )
        
        embed.add_field(name="Duration", value="0 seconds")
        embed.add_field(name="Author", value="AUTHOR")

        embed.set_author(
            name="Now playing...",
            icon_url="attachment://icon.png"
        )

        await ctx.send(embed=embed, view=Buttons(ctx), file=icon)


    class Buttons(discord.ui.View):
        def __init__(self, ctx):
            super().__init__(timeout=None)
            self.ctx = ctx

        @discord.ui.button(label="Prev.", style=discord.ButtonStyle.secondary)
        async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == self.ctx.author:
                await interaction.response.defer()
                print("Prev.")
                # await previous(self.ctx)

        @discord.ui.button(label="Pause", style=discord.ButtonStyle.secondary)
        async def pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == self.ctx.author:
                await interaction.response.defer()
                await pause(self.ctx)

        @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger)
        async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == self.ctx.author:
                await interaction.response.defer()
                await stop(self.ctx)

        @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
        async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == self.ctx.author:
                await interaction.response.defer()
                print("Next")
                # await next(self.ctx)

        @discord.ui.button(label="Loop", style=discord.ButtonStyle.secondary)
        async def loop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == self.ctx.author:
                await interaction.response.defer()
                await toggle_loop(self.ctx)


    client.run(TOKEN)
