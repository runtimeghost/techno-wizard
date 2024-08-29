# pylint: disable=bad-indentation

# Rewriting mirror extension with with more commands and Cancel support

from os import remove, curdir, path, listdir, mkdir, environ
from io import BytesIO
from shutil import rmtree
from json import dumps, dump, load
from random import choices
from string import ascii_letters
from contextlib import suppress
from flask import Flask, render_template_string, request
from threading import Thread
from discord.ext import commands
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from aiohttp import FormData, ClientSession, ClientTimeout, client_exceptions
from aiofiles import open as aopen
from asyncio import sleep as asleep
import discord

from bot_ui import ConfirmButtons, CancelMirror


mirror_tasks = {}
auth_flows = {}

SCOPES = ["https://www.googleapis.com/auth/drive"]

authorization_flow_handler = Flask(__name__)

@authorization_flow_handler.route('/')
def auth_flow():
    user_id = request.args.get('state')
    code = request.args.get('code')
    if code and user_id:
        user_id = int(user_id)
        flow: Flow = auth_flows[user_id]
        flow.fetch_token(code=code)
        with open(f'{curdir}/database/drive_creds/{user_id}.json', 'w') as user_file:
            user_file.write(flow.credentials.to_json())
        auth_flows.pop(user_id)
        return render_template_string(
            """
<!Doctype html>

<html>
    <head>
        <title>Authorization Successful</title>
    </head>
    <body>
        <h1>Authorization Successful</h1>
        <br/>
        <h2>Thank you for logging in. Now you can use the <code>/mirror</code> command.</h2>
        <p><b>You can close this tab now</b></p>
    <body>
</html>
            """
        )
    else:
        return render_template_string(
            """
<!Doctype html>

<html>
    <head>
        <title>Authorization Error</title>
    </head>
    <body>
        <h1>Authorization Failed somehow</h1>
        <h2>Something went wrong please try again using the <code>/login</code> command in the bot's inbox (DM)</h2>
        <p>You can close this tab now</p>
    <body>
</html>
            """
        )

def refreshed_drive_creds(user_id: int|str):

    """Gets refreshed Tokens for google drive access"""

    token = f"{curdir}/database/drive_creds/{user_id}.json"
    creds = Credentials.from_authorized_user_file(token, SCOPES)
    while True:
        if creds.expired or not creds.valid:
            creds.refresh(Request())
            with open(token, 'w') as tokenfile:
                tokenfile.write(creds.to_json())
        return creds


# DRIVE_CREDS = refreshed_drive_creds()

# def create_authorized_tokenfile():
#     flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
#     creds = flow.run_local_server(port=0)
#     with open("token.json", "w") as f:
#          f.write(creds.to_json())
#     return creds


class MirrorableFile:

    """File object that is to be mirrored"""

    def __init__(self, ctx, session, file_id, url: str):

        """Constructing our file object that we will be downloaded"""

        self.ctx = ctx
        self.session = session
        self.url = url
        self.id = file_id
        self.drive_id = url.split('/')[5] if 'drive.google.com' in url else None
        self.name = f"<{ctx.author.id}_unknown_file>"
        self.drive_folder = None
        self.directory = f"{curdir}/downloads/{ctx.author.id}/"
        self.filepath = self.directory+self.name
        self.total_size = 1 # Default set to 1 just stay safe from ZeroDivisionError :)
        self.uploaded_file_info = None
        self.status = None
        self.download_task = None


    def delete(self):
        with suppress(KeyError):
            del mirror_tasks[self.id]
        with suppress(FileNotFoundError):
            remove(self.filepath)


    def update_progressbar(self, tillnow):
        pos = round(tillnow / self.total_size * 25)
        tillnow_mb = round(tillnow / pow(1024, 2), 2)
        total_mb = round(self.total_size / pow(1024, 2), 2)
        progressbar = "".join("-" if pos < x else "=" for x in range(1, 26))
        desc = f"""
|{progressbar}|{round(tillnow/self.total_size*100)}%
{tillnow_mb} MB of {total_mb} MB |
File name: {self.name}
"""
        return desc


    async def create_folder(self):
        headers = {
            "Authorization": f"Bearer {refreshed_drive_creds(self.ctx.author.id).token}",
            "User-agent": "Mozilla/5.0 (X11; Linux x86_64; rv:39.0) Gecko/20100101 Firefox/39.0"
        }
        filemeta = {"name": "TechnoWizard-Mirrors", "mimeType": "application/vnd.google-apps.folder"}
        async with self.session.post("https://www.googleapis.com/drive/v3/files", headers=headers, json=filemeta) as resp:
            folder = await resp.json()
        folder_id = folder.get('id')
        with open(f'{curdir}/database/folders.json', 'r') as f:
            folders = load(f)
        folders[self.ctx.author.id] = folder_id
        with open(f'{curdir}/database/folders.json', 'w') as f:
            dump(folders, f, indent=4)
        perms = {'role': 'reader', 'type': 'anyone'}
        await self.session.post(f'https://www.googleapis.com/drive/v3/files/{folder_id}/permissions', headers=headers, json=perms)
        return folder


    async def get_folder_from_drive(self):
        headers = {
            "Authorization": f"Bearer {refreshed_drive_creds(self.ctx.author.id).token}",
            "User-agent": "Mozilla/5.0 (X11; Linux x86_64; rv:39.0) Gecko/20100101 Firefox/39.0"
        }
        query = f"name='TechnoWizard-Mirrors' and trashed=false and mimeType='application/vnd.google-apps.folder' and sharedWithMe=false"
        params = {"fields": "files(name, id)", 'q': query}
        async with self.session.get("https://www.googleapis.com/drive/v3/files", headers=headers, params=params) as resp:
            datas = await resp.json()
        files = datas.get("files")
        return files[0] if files else await self.create_folder()


    async def get_folder_id(self):
        with open(f"{curdir}/database/folders.json") as f:
            folder_ids = load(f)
        user_folder = folder_ids.get(self.ctx.author.id)
        if not user_folder:
            user_folder = await self.get_folder_from_drive()
        self.drive_folder = user_folder.get('id')
        return self.drive_folder

    async def send_existing(self, drive_file_id):
        emb = discord.Embed(
            title="Same file found!",
            description="File already exists in the drive!",
            timestamp=discord.utils.utcnow()
            )
        emb.add_field(name="File name", value=self.name)
        emb.set_thumbnail(url="https://www.shareicon.net/download/128x128//2016/07/09/118690_drive_512x512.png")
        emb.set_footer(text=self.ctx.bot.user.name)
        view = discord.ui.View(timeout=None)
        view.add_item(discord.ui.Button(
            label="Download",
            url=f"https://drive.google.com/file/d/{drive_file_id}/view?usp=drive_link"
            )
        )
        return await self.ctx.send(embed=emb, view=view)


    async def already_exists(self):
        headers = {
            "Authorization": f"Bearer {refreshed_drive_creds(self.ctx.author.id).token}",
            "User-agent": "Mozilla/5.0 (X11; Linux x86_64; rv:39.0) Gecko/20100101 Firefox/39.0"
        }
        if not self.drive_folder:
            await self.get_folder_id()
        query = f"'{self.drive_folder}' in parents and name = '{self.name}' and trashed = false and mimeType != 'application/vnd.google-apps.folder'"
        params = {"fields": "files(name, id)", 'q': query}
        async with self.session.get("https://www.googleapis.com/drive/v3/files", headers=headers, params=params) as resp:
            datas = await resp.json()
            try:
                files = datas["files"]
            except KeyError:
                return None
        return files[0] if files else None


    async def generate_name(self, response=None):
        if self.drive_id:
                header = {
                    "Authorization": f"Bearer {refreshed_drive_creds(self.ctx.author.id).token}",
                    'User-agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:39.0) Gecko/20100101 Firefox/39.0'
                }
                url = f"https://www.googleapis.com/drive/v3/files/{self.drive_id}"
                async with self.session.get(url, headers=header) as resp:
                    file = await resp.json()
                filename = file['name']
        else:
            headers = response.headers
            if "content-disposition" in headers:
                attachment: str = headers["content-disposition"]
                filename = attachment.removeprefix("attachment; filename=").strip('"\';')
                if ';' in filename:
                    filename = filename[:filename.find(';')]
            else:
                url = str(response.url)
                if '?' in url:
                    url = url.split('?', maxsplit=1)[0]
                filename = url.rsplit('/', maxsplit=1)[-1].split('?')[0].replace("%20", "_")
        if filename:
            self.name = filename
            self.filepath = self.directory+self.name
        return self.name


    async def download(self, save_to_drive=True):
        """Download this file"""

        head = {'User-agent': "Mozilla/5.0 (X11; Linux x86_64; rv:39.0) Gecko/20100101 Firefox/39.0"}
        async with self.session.get(self.url, headers=head, chunked=True) as resp:

            content_type = resp.headers.get("content-type")
            if content_type is not None and "text/html" in content_type:
                if self.ctx.interaction:
                    await self.ctx.send(
                    ":x: **The url you provided returned a webpage! Direct download link of the file is required.**",
                    ephemeral=True
                    )
                else:
                    await self.ctx.reply(":x: Url returned a website instead of a file.")
                return None

            await self.generate_name(resp)
            if existing_file:=await self.already_exists():
                return await self.send_existing(drive_file_id=existing_file['id'])

            if not path.exists(self.filepath):
                if self.ctx.interaction:
                    await self.ctx.send('Mirroring started...', delete_after=3)
                
                if not path.exists(self.directory):
                    mkdir(self.directory)

                emb = discord.Embed(
                    title="File Mirror",
                    description=f"{self.ctx.bot.infinity_emoji} Connecting...",
                    colour=discord.Colour.random(),
                    timestamp=discord.utils.utcnow()
                    )
                infos = [
                    {
                        "name": "File ID",
                        "value": f"`{self.id}`"
                    },
                    {
                        "name": "Server",
                        "value": resp.headers.get("server", "<unknown>")
                    },
                    {
                        "name":"Requested by",
                        "value": self.ctx.author.mention
                    }
                ]
                for info in infos:
                    emb.add_field(**info)
                emb.set_footer(text=self.ctx.bot.user.name)
                self.status = await self.ctx.channel.send(embed=emb, view=CancelMirror(self))

                self.total_size = int(resp.headers.get("content-length", 8000000))
                if self.total_size < 8000000:
                    return await self.ctx.send(
                        f":x:{self.ctx.author.mention} {self.name} can't be mirrored! Reason: Filesize too small ({round(self.total_size/pow(1024, 2), 2)} MB)"
                        )
                tillnow = 0
                async with aopen(self.filepath, "wb") as this_file:
                    rate_limiting_time = self.ctx.bot.loop.time()
                    async for data in resp.content.iter_chunked(8192):
                        tillnow += len(data)
                        await this_file.write(data)
                        if self.ctx.bot.loop.time() - rate_limiting_time > 4:
                            emb.description = self.update_progressbar(tillnow)
                            rate_limiting_time = self.ctx.bot.loop.time()
                            await self.status.edit(embed=emb)
                await self.status.delete()

        if save_to_drive:
            await self.upload(refreshed_drive_creds(self.ctx.author.id))

    async def upload(self, creds):
        emb = discord.Embed(
            title="File mirror",
            description=f"""
{self.ctx.bot.infinity_emoji} Uploading to drive please wait...
**File name**: {self.name}
""",
            colour=discord.Colour.random(),
            timestamp=discord.utils.utcnow()
        )
        infos = [
            {
                "name": "File ID",
                "value": f"`{self.id}`"
            },
            {
                "name": "File size",
                "value": f"{round(self.total_size / pow(1024, 2), 2)} MB"
            },
            {
                "name": "Server",
                "value": "Google Drive API"
            },
            {
                "name": "Requested by",
                "value": self.ctx.author.name
            }
        ]
        for info in infos:
            emb.add_field(**info)
        emb.set_footer(text=self.ctx.bot.user.name)
        self.status = await self.ctx.channel.send(embed=emb, view=CancelMirror(file_obj=self))
        if not self.drive_folder:
            await self.get_folder_id()
        filemeta = {"name": self.name, "parents": [self.drive_folder]}
        headers = {
            "Authorization": f"Bearer {creds.token}",
            "User-agent": "Mozilla/5.0 (X11; Linux x86_64; rv:39.0) Gecko/20100101 Firefox/39.0"
        }
        data = FormData()
        data.add_field("metadata", dumps(filemeta), content_type='application/json; charset=UTF-8')
        data.add_field("file", open(self.filepath, "rb"))
        async with self.session.post(
            "https://www.googleapis.com/upload/drive/v3/files",
            data=data, headers=headers, params={"uploadType": "multipart"},
            ) as resp:
            self.uploaded_file_info = await resp.json()
        emb.description = f""":white_check_mark: {self.ctx.author.mention} File successfully mirrored
File: `{self.uploaded_file_info.get("name")}`"""
        emb.insert_field_at(1, name="File Type", value=self.uploaded_file_info.get("mimeType") or "<unknown>")
        view = discord.ui.View(timeout=None)
        view.add_item(discord.ui.Button(
            label="Download",
            url=f"https://drive.google.com/file/d/{self.uploaded_file_info.get('id')}/view?usp=drive_link")
        )
        emb.set_thumbnail(url="https://www.shareicon.net/download/128x128//2016/07/09/118690_drive_512x512.png")
        await self.status.edit(embed=emb, view=view)
        self.delete()


    async def create_copy(self):
        await self.generate_name()
        if existing_file:=await self.already_exists():
            return await self.send_existing(drive_file_id=existing_file['id'])
        headers = {
            "Authorization": f"Bearer {refreshed_drive_creds(self.ctx.author.id).token}",
            "User-agent": "Mozilla/5.0 (X11; Linux x86_64; rv:39.0) Gecko/20100101 Firefox/39.0"
            }
        folder_id = await self.get_folder_id()
        filemeta = {"parents": [folder_id]}
        async with self.session.post(
            f"https://www.googleapis.com/drive/v3/files/{self.drive_id}/copy",
            data=dumps(filemeta),
            headers=headers) as resp:
            cloned_file = await resp.json()
        desc = f":white_check_mark: {self.ctx.author.mention} The File has been cloned"
        emb = discord.Embed(
            title="File clone",
            description=desc,
            colour=discord.Colour.random(),
            timestamp=discord.utils.utcnow()
            )
        emb.add_field(name="Filename", value=cloned_file.get("name", '<unknown>'))
        emb.add_field(name="File Type", value=cloned_file.get('mimeType', "<Unknown File Type>"))
        emb.set_thumbnail(url="https://www.shareicon.net/download/128x128//2016/07/09/118690_drive_512x512.png")
        emb.set_footer(text=self.ctx.bot.user.name)
        button = discord.ui.View(timeout=None)
        button.add_item(
            discord.ui.Button(
                label="Download",
                url=f"https://drive.google.com/file/d/{cloned_file['id']}/view?usp=drive_link"
                )
            )
        return await self.ctx.send(embed=emb, view=button)


    async def cancel(self):
        self.download_task.cancel()
        with suppress(discord.errors.NotFound):
            await self.status.delete()
        self.delete()
        await self.ctx.channel.send(f"{self.ctx.author.mention} You cancelled the mirror task :ballot_box_with_check:")

async def check(ctx):
    if not path.exists(f"{curdir}/database/drive_creds/{ctx.author.id}.json"):
        await ctx.send(":x: Google drive login required! Use `/login` command in the bot's inbox (DM)")
        return False
    else:
        return True


class MirrorFiles(commands.Cog):
    """The mirror commands class"""

    session: ClientSession

    def __init__(self, client):
        self.client = client
        if not path.exists(f'{curdir}/database/drive_creds'):
            mkdir(f"{curdir}/database/drive_creds")
        self.unsupported_urls = {
            "mega.": ":x: File urls from MEGA is not supported yet" 
        } # More unsupported url messages to be added later and need to add support for them in future


    async def cog_command_error(self, ctx, error):
        if isinstance(error, client_exceptions.InvalidURL):
            await ctx.send(":x: The download url is invalid!")
        elif isinstance(error, commands.PrivateMessageOnly):
            return await ctx.send(":x: This command is available in DM (inbox) only!")


    def unsupported(self, url) -> str|None:
        for unsupported_url in self.unsupported_urls:
            if unsupported_url in url:
                return self.unsupported_urls[unsupported_url]
        return None


    @commands.hybrid_command(usage='login')
    @commands.dm_only()
    async def login(self, ctx):
        """Login to grant access to your google drive"""
        if path.exists(f'{curdir}/database/drive_creds/{ctx.author.id}.json'):
            return await ctx.send(":ballot_box_with_check: You are already logged in to google drive. Use `/logout` to logout.")
        flow = Flow.from_client_secrets_file("credentials.json", SCOPES, redirect_uri='http://techno-wizard.eastus.cloudapp.azure.com')
        auth_flows[ctx.author.id] = flow
        embed = discord.Embed(
            title='Drive Login',
            description="Please click the login button to login into google drive.",
            timestamp=discord.utils.utcnow(), color=discord.Color.random()
            )
        embed.set_footer(text=self.client.user.name)
        view = discord.ui.View(timeout=None)
        view.add_item(discord.ui.Button(label='Login', url=flow.authorization_url(prompt='consent', access_type='offline', state=str(ctx.author.id))[0]))

        return await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(usage='logout')
    @commands.dm_only()
    async def logout(self, ctx):
        """Logout and revoke access from your google drive account"""
        if not path.exists(f'{curdir}/database/drive_creds/{ctx.author.id}.json'):
            return await ctx.send(f"You are not logged in! Please use `/login` to start login session")
        else:
            remove(f'{curdir}/database/drive_creds/{ctx.author.id}.json')
            return await ctx.send("Logged out from drive. :ballot_box_with_check:")

    @commands.hybrid_command(
        description="Mirror and get a google drive link",
        usage="mirror <direct download link>"
        )
    @discord.app_commands.describe(url="The direct download link of the file")
    async def mirror(self, ctx, url: str=""):
        if not url:
            return await ctx.send(":x: Please try again providing a direct download link of the file!")
        if msg:=self.unsupported(url):
            return await ctx.send(msg)
        if inter:=ctx.interaction:
            await inter.response.defer()
        else:
            await ctx.typing()
        file_id = "".join(choices(ascii_letters, k=10))
        while file_id in mirror_tasks: #| What if the randomly generated id gets matched with an already existing id? :) Yes! It's very rare.
            file_id = "".join(choices(ascii_letters, k=10))
        file_obj = MirrorableFile(ctx, self.session, file_id, url)
        file_obj.download_task = self.client.loop.create_task(file_obj.download())
        mirror_tasks[file_id] = file_obj
        await file_obj.download_task
        with suppress(KeyError):
            mirror_tasks.pop(file_id)


    @commands.hybrid_command(
        description="Create a clone from another google drive file",
        usage="clone <google_drive_file_link>"
    )
    @discord.app_commands.describe(url="The public url of the google drive file")
    async def clone(self, ctx, *, url: str=None):
        if "drive.google.com/" not in url:
            return await ctx.send(f":warning: This command is only for google drive links! Please use `{ctx.prefix}mirror` command instead!")
        if inter:=ctx.interaction:
            await inter.response.defer(thinking=False)
        else:
            await ctx.typing()
        file_obj = MirrorableFile(ctx, self.session, file_id="clone_task_no_id", url=url)
        await file_obj.create_copy()


    @commands.hybrid_command(
        description="Download and get a file uploaded in this channel",
        usage="leech <direct_download_link>"
        )
    @discord.app_commands.describe(url="The direct download link of the file")
    async def leech(self, ctx, *, url: str=None):
        if not url:
            return await ctx.send(":x: Please try again providing the download link!")
        async with self.session.get(url, chunked=True) as resp:
            leech_file = MirrorableFile(ctx, self.session, "leech-file-no-id", url)
            await leech_file.generate_name(resp)
            filename = leech_file.name
            filesize = float(resp.headers.get('content-length', 1))
            if inter:=ctx.interaction:
                await inter.response.defer()
            else:
                await ctx.typing()
            if filesize > 8283750.5:
                return await ctx.send(f":x: {ctx.author.mention} Your file can't be sent because discord doesn't allow sending files more than 8 MB!")
            filebytes = BytesIO()
            async for dat in resp.content.iter_chunked(1024):
                filebytes.write(dat)
            filebytes.seek(0)
            downloadedfile = discord.File(fp=filebytes, filename=filename)
            filesize_kb = round(filesize/1024, 2)
            str_filesize = f"{filesize_kb} KB" if filesize_kb < 1024 else f"{round(filesize_kb/1024, 2)} MB"
            desc = f"""
:white_check_mark: {ctx.author.mention} Leech task was successful!
**File name: {filename} | Total size: {str_filesize}**
"""
            await ctx.send(desc, file=downloadedfile)
        filebytes.close()


    @commands.hybrid_command(description="Cancel a running mirror task", usage="cancel <file_id>")
    @discord.app_commands.describe(file_id="The id of the file that is being mirrored currently")
    async def cancel(self, ctx, *, file_id: str=""):
        if not file_id:
            # Don't know what to close :) 
            return await ctx.send(":x: You did not provide any file id! Please try again with a file id.")
        try:
            file_obj = mirror_tasks[file_id]
            if file_obj.ctx.author not in (ctx.author, self.client.owner, ctx.guild.owner):
                if inter:=ctx.interaction:
                    return await inter.response.send_message("**:x: You are not the one who started this mirror task!**", ephemeral=True)
                return await ctx.send("**:x: You are not the one who started this mirror task!**", delete_after=5)
        except KeyError:
            return await ctx.send(":x: No file with this file id found!")
        if inter:=ctx.interaction:
            await inter.response.send_message("Cancelling...", delete_after=2)
        await file_obj.cancel()


    @commands.command(aliases=['del', 'delete'], hidden=True)
    @commands.is_owner()
    async def delete_a_file(self, ctx, drive_url):
        fileId = drive_url.split('/')[5]
        headers = {
            'Authorization': f"Bearer {refreshed_drive_creds(ctx.author.id).token}",
            "User-agent": "Mozilla/5.0 (X11; Linux x86_64; rv:39.0) Gecko/20100101 Firefox/39.0"}
        async with self.session.delete(f"https://www.googleapis.com/drive/v3/files/{fileId}", headers=headers) as response:
            if response.status == 204:
                await ctx.send(f"The file was removed from the drive successfully!\nFile id: `{fileId}`")
            elif response.status == 404:
                await ctx.send(f":x: The file with id `{fileId}` was not found in the drive!")
            else:
                return await ctx.send(response)


    @commands.command(aliases=["cs"], hidden=True)
    @commands.is_owner()
    async def cleanup(self, ctx, user: discord.User|None=None):
        folders = listdir(f"{curdir}/downloads/")
        if not folders:
            return await ctx.send(":warning: No files in downloads!")
        msg = f"Cleanup All mirrored files by {user}?" if user else "Are you sure to delete all mirrored files?"
        view = ConfirmButtons(timeout=40)
        emb = discord.Embed(
            title='Cleanup Storage',
            description=msg,
            colour=discord.Colour.random(),
            timestamp=discord.utils.utcnow()
        )
        emb.set_footer(text=self.client.user.name)
        msg = await ctx.send(
            embed=emb,
            view=view
        )
        await view.wait()
        if view.value is None:
            return await msg.delete()
        elif view.value == False:
            return await ctx.send("Cancelled!")
        else:
            emb.description = f"{self.client.infinity_emoji} Cleaning..."
            await msg.edit(embed=emb)
            await asleep(2) #| Not sure if this rate limit handling is necessary
            if user:
                user_directory = f'{curdir}/downloads/{user.id}/'
                if file_count:=len(listdir(user_directory)):
                    rmtree(user_directory)
                    emb.description = f"Cleared {file_count} files of {user}. :thumbsup:"
                else:
                    emb.description = f"No mirrored files by {user}"
                await msg.edit(embed=emb)
            else:
                user_count = len(folders)
                file_count = 0
                for folder in folders:
                    directory = f"{curdir}/downloads/{folder}"
                    file_count+=len(listdir(directory))
                    rmtree(directory)
                emb.description = f"Removed total {file_count} files of {user_count} users successfully :thumbsup:"
                await msg.edit(embed=emb)


auth_app_thread = Thread(target=authorization_flow_handler.run, kwargs={'host':environ.get("FLASK_HOST"), 'port': 8000})
auth_app_thread.daemon = True


async def setup(bot):
    print("Setting up Mirror commands....")
    if not path.exists(f"{curdir}/downloads"):
        mkdir(f"{curdir}/downloads")
    auth_app_thread.start()
    MirrorFiles.session = ClientSession(timeout=ClientTimeout(total=2*60*60))
    await bot.add_cog(MirrorFiles(bot))


async def teardown(bot):
    print("Unloading Mirror commands...")
    await MirrorFiles.session.close()
    await bot.remove_cog(bot.cogs["MirrorFiles"])

