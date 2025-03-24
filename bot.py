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

songs_folder = f"{os.getcwd()}\\Songs\\"
attachments_folder = f"{os.getcwd()}\\Attachments\\"

songbook_csv = f"{os.getcwd()}\\Songbook.csv"
songbook_data = pandas.read_csv(songbook_csv, delimiter=';')
songbook = None

# player variables
current_song = None
loop = True

queue = []
queue_index = 0

# songbook variables
groups = []
current_page = 0
total_pages = 0

# song select variables
selected_theme = None

# message IDs
player_id = 0
songbook_id = 0
song_select_id = 0
queue_id = 0

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
        for group, theme, path in songbook:
            if user_input.lower() == theme.lower():
                song_path = path;

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
            for group, theme, path in songbook:
                if user_input.lower() == theme.lower():
                    song_theme = theme
                    song_path = path
            
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
        clear_variables()

    def clear_variables():
        global current_song, loop, queue, queue_index, groups, current_page, total_pages, selected_theme
        
        # player variables
        current_song = None
        loop = True

        queue = []
        queue_index = 0

        # songbook variables
        groups = []
        current_page = 0
        total_pages = 0

        # song select variables
        selected_theme = None

        # message IDs
        player_id = 0
        songbook_id = 0
        song_select_id = 0
        queue_id = 0

    # PLAYER VIEW
    async def show_player(ctx):
        global player_id
        
        song_title = current_song.split("\\")[-1].split("(")[0].strip()
        song_category = current_song.split("\\")[-2]
        song_author = "D&D Breakfast Club"
        song_duration = get_duration(current_song)

        icon_path = f"{attachments_folder}\\icon.png"
        thumbnail_path = get_thumbnail(current_song)

        # attachments
        files = []

        with open(icon_path, "rb") as icon_file:
            icon = discord.File(icon_file, filename="icon.png")
            files.append(icon)

        if thumbnail_path:
            with open(thumbnail_path, "rb") as thumbnail_file:
                thumbnail = discord.File(thumbnail_file, filename="cover.jpg")
                files.append(thumbnail)

        # embed
        embed = discord.Embed(
            title = song_title,
            description = song_category,
            color = discord.Color.red(),
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
        
        # view
        view=PlayerView(ctx)

        message = await ctx.send("** **", embed=embed, view=view, files=files)
        player_id = message.id

    class PlayerView(discord.ui.View):
        def __init__(self, ctx):
            super().__init__(timeout=None)
            self.ctx = ctx

            # previous button
            self.previous_button = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Prev.", disabled=True)
            self.previous_button.callback = self.previous_callback
            self.add_item(self.previous_button)

            # pause/resume button
            self.pause_button = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Pause")
            self.pause_button.callback = self.pause_callback
            self.add_item(self.pause_button)

            # next button
            self.next_button = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Next", disabled=True)
            self.next_button.callback = self.next_callback
            self.add_item(self.next_button)

            # loop button
            self.loop_button = discord.ui.Button(style=discord.ButtonStyle.success, label="Loop")
            self.loop_button.callback = self.loop_callback
            self.add_item(self.loop_button)

        # callbacks
        async def previous_callback(self, interaction: discord.Interaction):
            global queue, queue_index
                
            if interaction.user == self.ctx.author:
                await interaction.response.defer()
                
                queue_index -= 1
                previous_song = list(queue[queue_index].values())[0]

                play_audio(self.ctx, previous_song)    

        async def pause_callback(self, interaction: discord.Interaction):
            if interaction.user == self.ctx.author:
                match self.pause_button.label:
                    case "Pause":
                        await pause(self.ctx)
                        self.pause_button.label = "Resume"
                        
                        await interaction.response.edit_message(content="", view=self)
                    case "Resume":
                        await resume(self.ctx)
                        self.pause_button.label = "Pause"
                        
                        await interaction.response.edit_message(content="", view=self)

        async def next_callback(self, interaction: discord.Interaction):
            global queue, queue_index
                
            if interaction.user == self.ctx.author:
                await interaction.response.defer()
                
                queue_index += 1
                next_song = list(queue[queue_index].values())[0]

                play_audio(self.ctx, next_song)
            
        async def loop_callback(self, interaction: discord.Interaction):
            global loop
            
            if interaction.user == self.ctx.author:
                await interaction.response.defer()
                await toggle_loop(self.ctx)

                if loop:
                    self.loop_button.style = discord.ButtonStyle.success
                else:
                    self.loop_button.style = discord.ButtonStyle.secondary

                await interaction.edit_original_response(content="", view=self)

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
        global songbook_id
        
        embed = discord.Embed(
            title = "Do’Lovaas’ Songbook",
            description = "This ancient book is filled with enchanted\nmelodies and forgotten secrets, offering every\nbard the perfectsong for any adventure.",
            color = discord.Color.blue()
        )

        view = SongbookClosedView(ctx)

        message = await ctx.send("** **", embed=embed, view=view)
        songbook_id = message.id

    class SongbookClosedView(discord.ui.View):
        def __init__(self, ctx):
            super().__init__(timeout=None)
            self.ctx = ctx

            # open button
            self.open_button = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Open")
            self.open_button.callback = self.open_callback
            self.add_item(self.open_button)

        # callbacks
        async def open_callback(self, interaction: discord.Interaction):
            global groups

            if interaction.user == self.ctx.author:
                for group, theme, path in songbook:
                    if group not in groups:
                        groups.append(group)

                embed = create_songbook_embed(1)
                view = SongbookOpenedView(ctx=self.ctx)
                
                # open sonbook
                message = await self.ctx.channel.fetch_message(songbook_id)
                await message.edit(content="", embed=embed, view=view)
                
                # show song select
                await show_song_select(self.ctx)

                await interaction.response.defer()

    class SongbookOpenedView(discord.ui.View):
        def __init__(self, ctx):
            super().__init__(timeout=None)
            self.ctx = ctx

            # previous button
            self.previous_button = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Prev.", disabled=True)
            self.previous_button.callback = self.previous_callback
            self.add_item(self.previous_button)

            # next button
            self.next_button = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Next")
            self.next_button.callback = self.next_callback
            self.add_item(self.next_button)

        # callbacks
        async def previous_callback(self, interaction: discord.Interaction):
            if interaction.user == self.ctx.author:
                embed = create_songbook_embed(current_page - 1)

                if current_page == 1:
                    self.previous_button.disabled = True
                    self.next_button.disabled = False
                else:
                    self.previous_button.disabled = False
                    self.next_button.disabled = True

                await interaction.response.edit_message(content="", embed=embed, view=self)  

        async def next_callback(self, interaction: discord.Interaction):
            if interaction.user == self.ctx.author:
                embed = create_songbook_embed(current_page + 1)
                
                if current_page == total_pages:
                    self.next_button.disabled = True
                    self.previous_button.disabled = False
                else:
                    self.next_button.disabled = False
                    self.previous_button.disabled = True

                await interaction.response.edit_message(content="", embed=embed, view=self)

    def create_songbook_embed(page):
        global current_page, total_pages

        group_filter = groups[page - 1]
        current_page = page
        total_pages = len(groups)

        filtered_songbook = [row for row in songbook if row[0] == group_filter]
                
        embed = discord.Embed(
            title = "Do’Lovaas’ Songbook",
            description = f"*{group_filter}*",
            color = discord.Color.blue()
        )

        embed.add_field(name=" ", value=" ", inline=False)

        for group, theme, path in filtered_songbook:
            if group == group_filter:
                song_title = path.split("\\")[-1].split("(")[0].strip()
                embed.add_field(name=theme, value=song_title, inline=False)

        embed.add_field(name=" ", value=" ", inline=False)
        embed.set_footer(text = f"Page {current_page}/{total_pages}")

        return(embed)

    # SONG SELECT VIEW
    async def show_song_select(ctx):
        embed = discord.Embed(
            title="Song Selection",
            description="Speak, brave soul — what song shall stir the fire this eve?",
            color=discord.Color.blue()
        )

        view = SongSelectView(ctx)

        song_select_id = await ctx.send("** **", embed=embed, view=view)

    class SongSelectView(discord.ui.View):
        def __init__(self, ctx):
            super().__init__()
            self.ctx = ctx

            # select menu
            self.select = create_select_menu()
            self.select.callback = self.select_callback
            self.add_item(self.select)

            # play button
            self.play_button = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Play", disabled=True)
            self.play_button.callback = self.play_callback
            self.add_item(self.play_button)

            # queue button
            self.queue_button = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Queue", disabled=True)
            self.queue_button.callback = self.queue_callback
            self.add_item(self.queue_button)

        # callbacks
        async def select_callback(self, interaction: discord.Interaction):
            global selected_theme
            selected_theme = interaction.data["values"][0]

            self.remove_item(self.select)
            self.select = create_select_menu()
            self.select.callback = self.select_callback
            self.add_item(self.select)

            self.play_button.disabled = False
            self.queue_button.disabled = False

            await interaction.response.edit_message(content="", view=self)

        async def play_callback(self, interaction: discord.Interaction):
            await interaction.response.defer()
            await play_from_songbook(self.ctx, selected_theme)

        async def queue_callback(self, interaction: discord.Interaction):
            await interaction.response.defer()
            await queue_song(self.ctx, user_input=selected_theme)

    def create_select_menu():
        options = []

        group_filter = groups[current_page - 1]
        filtered_songbook = [row for row in songbook if row[0] == group_filter]

        for group, theme, path in filtered_songbook:
            if theme == selected_theme:
                select_option = discord.SelectOption(label=theme, default=True)
            else:
                select_option = discord.SelectOption(label=theme, default=False)

            options.append(select_option)
        
        select = discord.ui.Select(
            placeholder="Select a theme...",
            min_values=1,
            max_values=1,
            options=options
        )

        return(select)

    # QUEUE VIEW
    async def show_queue(ctx):
        embed = create_queue_embed()
        view = QueueView(ctx)

        queue_id = await ctx.send("** **", embed=embed, view=view)

    class QueueView(discord.ui.View):
        def __init__(self, ctx):
            super().__init__(timeout=None)
            self.ctx = ctx

            # update button
            self.update_button = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Update")
            self.update_button.callback = self.update_callback
            self.add_item(self.update_button)

            # clear button
            self.clear_button = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Clear")
            self.clear_button.callback = self.clear_callback
            self.add_item(self.clear_button)

        # callbacks
        async def update_callback(self, interaction: discord.Interaction):
            await interaction.response.edit_message(content="", embed=create_queue_embed(), view=self)

        async def clear_callback(self, interaction: discord.Interaction):
            global queue
            
            match self.clear_button.style:
                case discord.ButtonStyle.secondary:
                    self.clear_button.style = discord.ButtonStyle.danger
                    
                    await interaction.response.edit_message(content="", view=self)
                case discord.ButtonStyle.danger:
                    self.clear_button.style = discord.ButtonStyle.secondary
                    queue = []

                    await interaction.response.edit_message(content="", embed=create_queue_embed(), view=self)

    def create_queue_embed():
        embed = discord.Embed(
            title = "Song Queue",
            description= "Behold — the ballads I’ll grace this tavern with tonight!",
            color = discord.Color.blue()
        )

        embed.add_field(name=" ", value=" ", inline=False)

        for song in queue:
            for theme, path in song.items():
                song_title = path.split("\\")[-1].split("(")[0].strip()

                if path == current_song:
                    embed.add_field(name=f"\> {theme}", value=song_title, inline=False)
                else:
                    embed.add_field(name=f"**-** {theme}", value=song_title, inline=False)

        return(embed)

    client.run(TOKEN)
