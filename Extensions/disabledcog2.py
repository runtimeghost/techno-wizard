# pylint: disable=bad-indentation


import os
import shutil
import json
import random
import asyncio

from string import ascii_letters
from typing import Optional
from discord.ext import commands

import discord
import aiohttp
import aiofiles

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from bot_ui import ConfirmButtons


SCOPES = ["https://www.googleapis.com/auth/drive"]


class MirrorLink(commands.Cog):

	session: aiohttp.ClientSession
	drive_token: str

	def __init__(self, client):
		self.client = client
		self.tasks = dict()
		self.drive_token = self.authorize_drive()

		if not os.path.exists(f"{os.curdir}/downloads"):
			os.mkdir(f"{os.curdir}/downloads")

	async def cog_command_error(self, ctx, error):
		print(error.__class__.__name__)
		print(str(error))
		if isinstance(error, TimeoutError):
			try:
				return await ctx.message.reply(":warning: File too large or Download Time is up!")
			except discord.errors.NotFound:
				return await ctx.send(f"{ctx.author.mention} Your task was cancelled for taking too much time!")
		else:
			print(str(error))
			#await self.client.dm_error_logs(error)


	def authorize_drive(self):
		creds = None
		if os.path.exists('token.json'):
			creds = Credentials.from_authorized_user_file('token.json', SCOPES)
			if creds.expired or creds.refresh_token:
				creds.refresh(Request())
			else:
				flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
				creds = flow.run_local_server(port=0)
			with open('token.json', 'w', encoding='utf-8') as token:
				token.write(creds.to_json())
		else:
			flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
			creds = flow.run_local_server(host='127.0.0.1', port=1080)
			with open('token.json', 'w', encoding='utf-8') as token:
				token.write(creds.to_json())
		return creds.token


	def updated_progbar(self, current, total_size, start_time, percent, speed, str_eta, file_id):
		pos = round(current / total_size*25)
		progressbar = "".join(" " if x > pos else "█" for x in range(1, 26))
		total_time = divmod(round(self.client.loop.time()-start_time), 60)
		str_total_time = "{0[0]}h {0[1]}m {1}s".format(divmod(total_time[0], 60), total_time[1])
		description = f"""`|{progressbar}|` -- {percent}%
**{round(current/1024**2, 2)}MiB / {round(total_size/1024**2, 2)}MiB** \
@{str(round(speed/pow(1024, 2), 2))+'MiB/s' if speed > pow(1024, 2) else str(round(speed/1024, 2))+'KiB/s'}
| ETA: {str_eta} | Elapsed: {str_total_time}
**File ID**: `{file_id}`"""
		return description

	async def write_to_disk_and_upload(self, ctx, msg, url, m_emb, filename, file_id):
		# Writing to disk

		current, percent, speed, eta = 0, 0, 0, 0
		async with self.session.get(url, chunked=True) as response:
			total_size = float(response.headers.get('content-length', 1))
			m_emb.title = "Downloading..."
			async with aiofiles.open(filename, 'wb') as afile:
				rate_limiting_time = self.client.loop.time()
				speed_time = self.client.loop.time()
				start_time = self.client.loop.time()
				async for dat in response.content.iter_any():
					if not dat or len(dat)==0:
						continue
					await afile.write(dat)
					current += len(dat)
					speed = round(len(dat)/(self.client.loop.time()-speed_time), 2)
					percent = round(current / total_size * 100, 2)
					try:
						eta = divmod(round(((total_size-current)/pow(1024, 2))/(speed/pow(1024, 2))), 60)
						str_eta = "{0[0]}h {0[1]}m {1}s".format(divmod(eta[0], 60), eta[1])
					except ZeroDivisionError:
						eta = 0
						str_eta = "<calculating>"
					speed_time = self.client.loop.time()
					if self.client.loop.time() - rate_limiting_time > 3: #| Handling rate limits
						m_emb.description = self.updated_progbar(
							current, total_size, start_time, percent, speed, str_eta, file_id
							)
						rate_limiting_time = self.client.loop.time()
						await msg.edit(embed=m_emb)
				await msg.delete()
				await self.upload(ctx, file_dir=filename)


	async def download(self, ctx: commands.Context, url: str):
		filename = f"{os.curdir}/downloads/{ctx.author.id}/{url.rsplit('/', 1)[-1]}"
		if os.path.exists(filename):
			await ctx.send(":warning: File Already Exists!")
			return False
		file_id = "".join(random.choice(ascii_letters) for _ in range(8))
		while file_id in self.tasks.keys():
			file_id = "".join(random.choice(ascii_letters) for _ in range(8))
		m_emb = discord.Embed(
			title="Connecting...",
			description=f"{self.client.infinity_emoji} Awaiting response...",
			colour=discord.Colour.random(),
			timestamp=discord.utils.utcnow()
		)
		m_emb.set_footer(text=self.client.user.name)
		msg = await ctx.channel.send(embed=m_emb)
		try:
			self.tasks[file_id] = self.client.loop.create_task(
				self.write_to_disk_and_upload(ctx,
					msg, url, m_emb, filename, file_id
				)
			)
		except asyncio.CancelledError:
			if os.path.exists(filename):
				os.remove(filename)
			m_emb.description = f"{ctx.author.mention} You task was cancelled successfully"


	async def upload(self, ctx, file_dir):
		me_emb = discord.Embed(
			title="Uploading to Google Drive",
			description=f"{self.client.infinity_emoji} File is being uploaded to google drive please wait",
			colour=discord.Colour.random(),
			timestamp=discord.utils.utcnow()
		)
		me_emb.set_footer(text=self.client.user.name)
		msg = await ctx.channel.send(embed=me_emb)
		self.drive_token = self.authorize_drive()
		file_metadata = {"name": os.path.split(file_dir)[1], "parents": ["1jf4CeBktLE7nDQFSatybjcSgkLrYCSwD",]}
		data = aiohttp.FormData()
		data.add_field('metadata', json.dumps(file_metadata), content_type='application/json; charset=UTF-8')
		data.add_field("file", open(file_dir, 'rb'))
		headers = {"Authorization": f"Bearer {self.drive_token}"}
		params = {'uploadType': 'multipart'}
		response = await self.session.post("https://www.googleapis.com/upload/drive/v3/files", data=data, params=params, headers=headers)
		await msg.delete()
		file_info = await response.json()
		downloaded_file = file_info.get("name")
		file_mimetype = file_info.get("mimeType")
		uploaded_file_id = file_info.get("id")
		success_emb = discord.Embed(
				title="File Mirror",
				description=f"{ctx.author.mention} Click the download button below :white_check_mark:",
				color=discord.Color.random(),
				timestamp=discord.utils.utcnow()
				)
		success_emb.set_thumbnail(
				url="https://www.shareicon.net/download/128x128//2016/07/09/118690_drive_512x512.png"
				)
		success_emb.add_field(name="Filename", value=downloaded_file)
		success_emb.add_field(name="File Type", value=file_mimetype)
		success_emb.set_footer(text=self.client.user.name)
		download_button = discord.ui.View(timeout=None)
		download_button.add_item(
			discord.ui.Button(
				label="Download",
				url=f"https://drive.google.com/file/d/{uploaded_file_id}/view?usp=drivesdk"
			)
		)
		return await ctx.channel.send(embed=success_emb, view=download_button)


	@commands.hybrid_command(name="cancel", description="Cancel a running download session", usage="cancel <file_id>")
	@discord.app_commands.describe(file_id="The 8 characters long id you were given")
	async def cancel_download(self, ctx, file_id: str):
		try:
			task = self.tasks.pop(file_id)
		except KeyError:
			return await ctx.send(f"No downloads corresponding to `{file_id}` was found!")
		task.cancel()
		return await ctx.send(f"Cancelling task `{file_id}`", delete_after=2)

	@commands.hybrid_command(
		aliases=['leech'],
		description="Mirror and get a google drive link",
		usage="mirror <direct download link>"
		)
	@discord.app_commands.describe(url="The direct Download link of the file")
	async def mirror(self, ctx, *, url: str=""):
		if not url:
			return await ctx.send(":x: Please provide a direct download link`!")
		if not os.path.exists(f"downloads/{ctx.author.id}"):
			os.mkdir(f'downloads/{ctx.author.id}')
		if "drive.google.com" in url:
			return await ctx.send(f":warning: For any Google Drive link Please use `{ctx.prefix}clone`")
		await ctx.send("Getting response....", delete_after=2)
		await self.download(ctx, url)

	@mirror.error
	async def mirror_err(self, ctx, error):
		if isinstance(error, aiohttp.client_exceptions.ClientConnectorError):
			return await ctx.send(":x: Can't Access resources from the given url!")


	@commands.hybrid_command(
			name="clone",
			description="Clone a file from google drive",
			usage="clone <google drive url>"
			)
	@commands.is_owner()
	@discord.app_commands.describe(url="The publicly shareable google drive url of the file")
	async def drive_clone(self, ctx, *, url: str=''):
		print(url)
		return await ctx.send(":x: This command is under development!")


	@commands.command(name="cleanup", aliases=['cs'], hidden=True)
	@commands.is_owner()
	async def cleanup_storage(self, ctx, *, user: Optional[discord.User]=None):
		folders = os.listdir(f"{os.curdir}/downloads/")
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
		if view.value == False:
			return await ctx.send("Cancelled!")
		emb.description = f"{self.client.infinity_emoji} Cleaning..."
		await msg.edit(embed=emb)
		await asyncio.sleep(2) #| Not sure if this rate limit handling is necessary
		if user:
			user_directory = f'{os.curdir}/downloads/{user.id}/'
			if file_count:=len(os.listdir(user_directory)):
				shutil.rmtree(user_directory)
				emb.description = f"Cleared {file_count} files of {user}. :thumbsup:"
			else:
				emb.description = f"No mirrored files by {user}"
			return await msg.edit(embed=emb)
		else:
			user_count = len(folders)
			file_count = 0
			for folder in folders:
				directory = f"{os.curdir}/downloads/{folder}"
				file_count+=len(os.listdir(directory))
				shutil.rmtree(directory)
			emb.description = f"Removed total {file_count} files of {user_count} users successfully :thumbsup:"
			return await msg.edit(embed=emb)


async def setup(client):
	print("Setting up Mirror commands")
	MirrorLink.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=6*3600))
	await client.add_cog(MirrorLink(client))

async def teardown(client):
	print("Unloading Mirror commands...")
	await MirrorLink.session.close()
	await client.remove_cog(client.cogs['MirrorLink'])

