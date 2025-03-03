import os
import pandas
import discord
from discord.ext import commands

# —————————————————————————————————————— #

TOKEN = os.getenv('discord_token')

intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix=".", intents=intents)

songbook_csv = f"{os.getcwd()}\\Settings\\Songbook.csv"
songbook = pandas.read_csv(songbook_csv, delimiter=';') 

current_audio = None
loop = True

# —————————————————————————————————————— #

def run_bot():
    @client.event
    async def on_ready():
        print(f"{client.user} is running.")

    # JOIN
    @client.command(name="join", aliases=["j"])
    async def join(ctx):
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await channel.connect()

    # PLAY
    @client.command(name="play", aliases=["p"])
    async def play(ctx, message: str):
        global current_audio
        vc = ctx.voice_client
        file_path = "";
        
        if not vc:
            await ctx.send("Hey! I'm not there yet!")
        else:
            # read songbook
            for index, row in songbook.iterrows():
                theme = row.iloc[0];
                path = row.iloc[1];

                if message.lower() == theme.lower():
                    file_path = path;

            # play audio
            if os.path.exists(file_path):
                current_audio = file_path
                vc.stop()
                play_audio(ctx, vc, file_path)
                await show_controls(ctx)
            else:
                await ctx.send("Sorry, I can't find that in my songbook.")

    def play_audio(ctx, vc, file_path):
        vc.play(
            discord.FFmpegPCMAudio(file_path),
            after=lambda e: check_loop(ctx, vc)
        )

    def check_loop(ctx, vc):
        if loop:
            play_audio(ctx, vc, current_audio)

    # PAUSE
    @client.command(name="pause")
    async def pause(ctx):
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()

    # RESUME 
    @client.command(name="resume")
    async def resume(ctx):
        if not ctx.voice_client.is_playing():
            ctx.voice_client.resume()

    # DISCONNECT
    @client.command(name="disconnect", aliases=["d"])
    async def disconnect(ctx):
        await ctx.voice_client.disconnect()

    # LOOP
    @client.command(name="loop", aliases=["l"])
    async def toggle_loop(ctx):
        global loop
        loop = not loop


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
                # await previous(self.ctx)

        @discord.ui.button(label="Pause", style=discord.ButtonStyle.secondary)
        async def pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == self.ctx.author:
                await interaction.response.defer()

                if button.label == "Pause":
                    await pause(self.ctx)
                    button.label = "Resume"
                else:
                    await resume(self.ctx)
                    button.label = "Pause"

                await interaction.edit_original_response(view=self)

        @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger)
        async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == self.ctx.author:
                await interaction.response.defer()
                await disconnect(self.ctx)

        @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
        async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == self.ctx.author:
                await interaction.response.defer()
                # await next(self.ctx)

        @discord.ui.button(label="Loop", style=discord.ButtonStyle.success)
        async def loop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == self.ctx.author:
                await interaction.response.defer()
                await toggle_loop(self.ctx)

                if loop:
                    button.style = discord.ButtonStyle.success
                else:
                    button.style = discord.ButtonStyle.secondary

                await interaction.edit_original_response(view=self)


    client.run(TOKEN)
