import os
import ffmpeg
import pandas
import discord
from discord.ext import commands

# —————————————————————————————————————— #

TOKEN = os.getenv('discord_token')

intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix=".", intents=intents)

attachments_folder = f"{os.getcwd()}\\Attachments\\"
songs_folder = f"{os.getcwd()}\\Songs\\"

songbook_csv = f"{os.getcwd()}\\Songbook.csv"
songbook_data = pandas.read_csv(songbook_csv, delimiter=';')
songbook = None

groups = []
current_page = 0
total_pages = 0

current_song = None
loop = True

queue = []
queue_index = 0

# —————————————————————————————————————— #

def run():
    @client.event
    async def on_ready():
        print(f"{client.user} is running.")

    # JOIN
    @client.command(name="join", aliases=["j"])
    async def join(ctx):
        global songbook

        # read songbook
        songbook = [row.tolist() for _, row in songbook_data.iterrows()]
        
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await channel.connect()

        await show_songbook(ctx)

    # PLAY
    @client.command(name="play", aliases=["p"])
    async def play(ctx, *, user_input: str = None):
        if not ctx.voice_client:
            await ctx.send("Hey! I'm not there yet!")
        else:
            if user_input is None:
                await play_from_queue(ctx)
            else:
                await play_from_songbook(ctx, user_input)
            
    async def play_from_queue(ctx):
        global queue, queue_index

        if queue != []:
            if not ctx.voice_client.is_playing():
                song_path = list(queue[queue_index].values())[0]

                play_audio(ctx, song_path)
                await show_player(ctx)
            else:
                await ctx.send("I'm already playing this beautiful melody... don't bother me!")

        else:
            await ctx.send("I got nothing to play.")

    async def play_from_songbook(ctx, user_input):
        song_path = '';

        # find song to play
        for group, theme, file in songbook:
            if user_input.lower() == theme.lower():
                song_path = file;

        # play audio
        if os.path.exists(song_path):
            play_audio(ctx, song_path)
            await show_player(ctx)
        else:
            await ctx.send("Sorry, I can't find that in my songbook.")

    def play_audio(ctx, song_path):
        global current_song

        if song_path != current_song:
            current_song = song_path
                
        ctx.voice_client.stop()

        ctx.voice_client.play(
            discord.FFmpegPCMAudio(song_path),
            after=lambda e: check_loop(ctx)
        )

    def check_loop(ctx):
        global queue, queue_index

        if loop:
            play_audio(ctx, current_song)
        else:
            queue_index += 1
            next_song = list(queue[queue_index].values())[0]

            play_audio(ctx, next_song)

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

    # LOOP
    @client.command(name="loop", aliases=["l"])
    async def toggle_loop(ctx):
        global loop

        loop = not loop

    # QUEUE
    @client.command(name="queue", aliases=["q"])
    async def queue_song(ctx, *, user_input: str = None):
        global queue, queue_index

        song_theme = ''
        song_path = ''

        if user_input is None:
            await show_queue(ctx)
        else:
            # find song to queue
            for group, theme, file in songbook:
                if user_input.lower() == theme.lower():
                    song_theme = theme
                    song_path = file
            
            # queue song
            if os.path.exists(song_path):
                queue.append({song_theme:song_path})

                await ctx.send("Another verse joins the sacred scroll of melodies, soon to echo through the realms.")
            else:
                await ctx.send("Sorry, I can't find that in my songbook.")

    # DISCONNECT
    @client.command(name="disconnect", aliases=["d"])
    async def disconnect(ctx):
        await ctx.voice_client.disconnect()

    # PLAYER VIEW
    async def show_player(ctx):
        song_title = current_song.split("\\")[-1].split("(")[0].strip()
        song_category = current_song.split("\\")[-2]
        song_author = "D&D Breakfast Club"
        song_duration = get_duration(current_song)

        icon_path = f"{attachments_folder}\\icon.png"
        thumbnail_path = get_thumbnail(current_song)

        # player attachments
        files = []

        with open(icon_path, "rb") as icon_file:
            icon = discord.File(icon_file, filename="icon.png")
            files.append(icon)

        if thumbnail_path:
            with open(thumbnail_path, "rb") as thumbnail_file:
                thumbnail = discord.File(thumbnail_file, filename="cover.jpg")
                files.append(thumbnail)

        # player structure
        embed = discord.Embed(
            title = song_title,
            description = f"*{song_category}*",
            color = discord.Color.red()
        )

        embed.set_author(
            name = "Now playing...",
            icon_url = "attachment://icon.png"
        )

        embed.set_thumbnail(url="attachment://cover.jpg")

        embed.add_field(name=" ", value=" ", inline=False)
        embed.add_field(name="Author", value=song_author, inline=True)
        embed.add_field(name=" ", value=" ", inline=True)
        embed.add_field(name="Duration", value=song_duration, inline=True)
        
        view=PlayerView(ctx)

        await ctx.send(embed=embed, view=view, files=files)

    class PlayerView(discord.ui.View):
        def __init__(self, ctx):
            super().__init__(timeout=None)
            self.ctx = ctx

        @discord.ui.button(label="Prev.", style=discord.ButtonStyle.secondary)
        async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            global queue, queue_index
            
            if interaction.user == self.ctx.author:
                await interaction.response.defer()
                
                queue_index -= 1
                previous_song = list(queue[queue_index].values())[0]

                play_audio(self.ctx, previous_song)                

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

        @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
        async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            global queue, queue_index
            
            if interaction.user == self.ctx.author:
                await interaction.response.defer()
                
                queue_index += 1
                next_song = list(queue[queue_index].values())[0]

                play_audio(self.ctx, next_song)  

        @discord.ui.button(label="Loop", style=discord.ButtonStyle.success)
        async def loop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            global loop
            
            if interaction.user == self.ctx.author:
                await interaction.response.defer()
                await toggle_loop(self.ctx)

                if loop:
                    button.style = discord.ButtonStyle.success
                else:
                    button.style = discord.ButtonStyle.secondary

                await interaction.edit_original_response(view=self)

    def get_duration(file_path):
        probe = ffmpeg.probe(file_path)
        duration = float(probe['format']['duration'])
        minutes = int(duration // 60)
        seconds = int(duration % 60)

        return f"{minutes}m {seconds:02d}s"

    def get_thumbnail(file_path):
        output_image = f"{attachments_folder}\\cover.jpg"

        # check the file's metadata for a video stream
        probe = ffmpeg.probe(file_path)
        video_streams = [stream for stream in probe['streams'] if stream['codec_type'] == 'video']

        if video_streams:
            (
                ffmpeg
                .input(file_path, ss=1)             # skip to 1 second
                .output(output_image, vframes=1)    # extract one frame only
                .run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
            )

            # return the path of the extracted image
            return output_image  
        else:
            return None

    # SONGBOOK VIEW
    @client.command(name="songbook", aliases=["s", "b"])
    async def show_songbook(ctx):
        embed = discord.Embed(
            title = "Do'Lovaas' songbook",
            description = "This ancient book is filled with enchanted\nmelodies and forgotten secrets, offering every\nbard the perfectsong for any adventure.",
            color = discord.Color.red()
        )

        view = SongbookClosedView(ctx)

        await ctx.send(embed=embed, view=view)

    class SongbookClosedView(discord.ui.View):
        def __init__(self, ctx):
            super().__init__(timeout=None)
            self.ctx = ctx

        @discord.ui.button(label="Open", style=discord.ButtonStyle.secondary)
        async def open(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == self.ctx.author:
                global groups

                for group, theme, file in songbook:
                    if group not in groups:
                        groups.append(group)

                embed = create_songbook_embed(1)
                view = SongbookOpenedView(ctx=self.ctx)
                
                await interaction.response.edit_message(embed=embed, view=view)

    class SongbookOpenedView(discord.ui.View):
        def __init__(self, ctx):
            super().__init__(timeout=None)
            self.ctx = ctx

        @discord.ui.button(label="Prev.", style=discord.ButtonStyle.secondary, disabled=True)
        async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == self.ctx.author:
                embed = create_songbook_embed(current_page - 1)
                self.update_buttons()

                await interaction.response.edit_message(embed=embed, view=self)

        @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
        async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == self.ctx.author:
                embed = create_songbook_embed(current_page + 1)
                self.update_buttons()

                await interaction.response.edit_message(embed=embed, view=self)

        def update_buttons(self):
            for child in self.children:
                if isinstance(child, discord.ui.Button):
                    if child.label == "Prev.":
                        child.disabled = (current_page == 1)
                    elif child.label == "Next":
                        child.disabled = (current_page == total_pages)

    def create_songbook_embed(page):
        global current_page, total_pages

        group_filter = groups[page - 1]
        current_page = page
        total_pages = len(groups)

        filtered_songbook = [row for row in songbook if row[0] == group_filter]
                
        embed = discord.Embed(
            title = "Do'Lovaas' songbook",
            description = f"*{group_filter}*",
            color = discord.Color.red()
        )

        embed.add_field(name=" ", value=" ", inline=False)

        for group, theme, file in filtered_songbook:
            if group == group_filter:
                song_title = file.split("\\")[-1].split("(")[0].strip()
                embed.add_field(name=theme, value=song_title, inline=False)

        embed.add_field(name=" ", value=" ", inline=False)
        embed.set_footer(text = f"Page {current_page}/{total_pages}")

        return(embed)

    # QUEUE VIEW
    async def show_queue(ctx):
        embed = discord.Embed(
            title = "Queue",
            description= "Behold the ballads and lays I am destined to perform:",
            color = discord.Color.red()
        )

        embed.add_field(name=" ", value=" ", inline=False)

        for song in queue:
            for theme, path in song.items():
                song_title = path.split("\\")[-1].split("(")[0].strip()

                if path == current_song:
                    embed.add_field(name=f"\> {theme}", value=song_title, inline=False)
                else:
                    embed.add_field(name=f"- {theme}", value=song_title, inline=False)

        view = QueueView(ctx)

        await ctx.send(embed=embed, view=view)

    class QueueView(discord.ui.View):
        def __init__(self, ctx):
            super().__init__(timeout=None)
            self.ctx = ctx

        @discord.ui.button(label="Update", style=discord.ButtonStyle.secondary)
        async def update(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == self.ctx.author:
                await interaction.response.defer()

        @discord.ui.button(label="Clear", style=discord.ButtonStyle.danger)
        async def clear(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == self.ctx.author:
                await interaction.response.defer()


    client.run(TOKEN)
