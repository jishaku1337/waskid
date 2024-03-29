
import sys, os, discord
from discord.ext import commands
from typing import Union
import logging

info_logger = logging.getLogger("info")
warning_logger = logging.getLogger('warning')
error_logger = logging.getLogger('error')

class GoodRole(commands.Converter):
  async def convert(self, ctx: commands.Context, argument): 
    try: role = await commands.RoleConverter().convert(ctx, argument)
    except commands.BadArgument: role = discord.utils.get(ctx.guild.roles, name=argument) 
    if role is None: 
      role = ctx.find_role(argument)
      if role is None: raise commands.BadArgument(f"Unable to find **role** with name **{argument}**") 
    if role.position >= ctx.guild.me.top_role.position: raise commands.BadArgument("This role **cannot** be managed by the bot (**maybe its above**)") 
    if ctx.author.id == ctx.guild.owner_id: return role 
    if role.position >= ctx.author.top_role.position: raise commands.BadArgument(f"You **cannot** manage this role")
    return role

class NoStaff(commands.Converter): 
  async def convert(self, ctx: commands.Context, argument): 
    try: member = await commands.MemberConverter().convert(ctx, argument)
    except commands.BadArgument: member = discord.utils.get(ctx.guild.members, name=argument)
    if member is None: raise commands.BadArgument(f"Unable to find **member** with name **{argument}**")  
    if member.id == ctx.guild.me.id: raise commands.BadArgument("why") 
    if member.top_role.position >= ctx.guild.me.top_role.position: raise commands.BadArgument(f"The bot cannot execute the command on **{member}**") 
    if ctx.author.id == ctx.guild.owner_id: return member
    if member.top_role.position >= ctx.author.top_role.position or member.id == ctx.guild.owner_id: raise commands.BadArgument(f"**Can't** use this command on **{member}**") 
    return member

class InvokeClass:
 
 async def invoke_send(ctx: commands.Context, member: Union[discord.User, discord.Member], reason: str): 
  res = await ctx.bot.db.fetchrow("SELECT embed FROM invoke WHERE guild_id = $1 AND command = $2", ctx.guild.id, ctx.command.name)
  if res: 
     code = res['embed']
     try: 
      x = await EmbedBuilder.to_object(EmbedBuilder.embed_replacement(member, InvokeClass.invoke_replacement(member, code.replace("{reason}", reason))))
      await ctx.reply(content=x[0], embed=x[1], view=x[2])
     except: await ctx.reply(EmbedBuilder.embed_replacement(member, InvokeClass.invoke_replacement(member, code.replace("{reason}", reason)))) 
     return True 
  return False   
 
 def invoke_replacement(member: Union[discord.Member, discord.User], params: str=None):
  if params is None: return None
  if '{member}' in params: params=params.replace("{member}", str(member))
  if '{member.id}' in params: params=params.replace('{member.id}', str(member.id))
  if '{member.name}' in params: params=params.replace('{member.name}', member.name)
  if '{member.mention}' in params: params=params.replace('{member.mention}', member.mention)
  if '{member.discriminator}' in params: params=params.replace('{member.discriminator}', member.discriminator)
  if '{member.avatar}' in params: params=params.replace('{member.avatar}', member.display_avatar.url)
  return params

 async def invoke_cmds(ctx: commands.Context, member: Union[discord.Member, discord.User], embed: str) -> discord.Message:
  res = await ctx.bot.db.fetchrow("SELECT embed FROM invoke WHERE guild_id = $1 AND command = $2", ctx.guild.id, ctx.command.name)
  if res:
   code = res['embed']    
   if embed == "none": 
    await ctx.bot.db.execute("DELETE FROM invoke WHERE guild_id = $1 AND command = $2", ctx.guild.id, ctx.command.name)
    return await ctx.send_success( f"Deleted the **{ctx.command.name}** custom response")
   elif embed == "view": 
    em = discord.Embed(color=ctx.bot.color, title=f"invoke {ctx.command.name} message", description=f"```{code}```")
    return await ctx.reply(embed=em)
   elif embed == code: return await ctx.send_warning( f"Embed is already **configured** as the {ctx.command.name} custom response")
   else:
      await ctx.bot.db.execute("UPDATE invoke SET embed = $1 WHERE guild_id = $2 AND command = $3", embed, ctx.guild.id, ctx.command.name)
      return await ctx.send_success( f"Updated custom command **{ctx.command.name}** message to {'the embed' if '--embed' in embed else ''}\n```{embed}```")
  else: 
   await ctx.bot.db.execute("INSERT INTO invoke VALUES ($1,$2,$3)", ctx.guild.id, ctx.command.name, embed)
   return await ctx.send_success( f"Added custom command **{ctx.command.name}** message to {'the embed' if '--embed' in embed else ''}\n```{embed}```")

class EmbedBuilder:
 def ordinal(self, num: int) -> str:
   """Convert from number to ordinal (10 - 10th)""" 
   numb = str(num) 
   if numb.startswith("0"): numb = numb.strip('0')
   if numb in ["11", "12", "13"]: return numb + "th"
   if numb.endswith("1"): return numb + "st"
   elif numb.endswith("2"):  return numb + "nd"
   elif numb.endswith("3"): return numb + "rd"
   else: return numb + "th"    

 def get_parts(params):
    params=params.replace('{embed}', '')
    return [p[1:][:-1] for p in params.split('$v')]

 def embed_replacement(user: discord.Member, params: str=None):
    if params is None: return None
    if '{user}' in params:
        params=params.replace('{user}', str(user.name) + "#" + str(user.discriminator))
    if '{user.mention}' in params:
        params=params.replace('{user.mention}', user.mention)
    if '{user.name}' in params:
        params=params.replace('{user.name}', user.name)
    if '{user.avatar}' in params:
        params=params.replace('{user.avatar}', str(user.display_avatar.url))
    if '{user.joined_at}' in params:
        params=params.replace('{user.joined_at}', discord.utils.format_dt(user.joined_at, style='R'))
    if '{user.created_at}' in params:
        params=params.replace('{user.created_at}', discord.utils.format_dt(user.created_at, style='R'))
    if '{user.discriminator}' in params:
        params=params.replace('{user.discriminator}', user.discriminator)
    if '{guild.name}' in params:
        params=params.replace('{guild.name}', user.guild.name)
    if '{guild.count}' in params:
        params=params.replace('{guild.count}', str(user.guild.member_count))
    if '{guild.count.format}' in params:
        params=params.replace('{guild.count.format}', EmbedBuilder.ordinal(len(user.guild.members)))
    if '{guild.id}' in params:
        params=params.replace('{guild.id}', user.guild.id)
    if '{guild.created_at}' in params:
        params=params.replace('{guild.created_at}', discord.utils.format_dt(user.guild.created_at, style='R'))
    if '{guild.boost_count}' in params:
        params=params.replace('{guild.boost_count}', str(user.guild.premium_subscription_count))
    if '{guild.booster_count}' in params:
        params=params.replace('{guild.booster_count}', str(len(user.guild.premium_subscribers)))
    if '{guild.boost_count.format}' in params:
        params=params.replace('{guild.boost_count.format}', EmbedBuilder.ordinal(user.guild.premium_subscription_count))
    if '{guild.booster_count.format}' in params:
        params=params.replace('{guild.booster_count.format}', EmbedBuilder.ordinal(len(user.guild.premium_subscribers)))
    if '{guild.boost_tier}' in params:
        params=params.replace('{guild.boost_tier}', str(user.guild.premium_tier))
    if '{guild.vanity}' in params: 
        params=params.replace('{guild.vanity}', "/" + user.guild.vanity_url_code or "none")         
    if '{invisible}' in params: 
        params=params.replace('{invisible}', '4b1218') 
    if '{botcolor}' in params: 
        params=params.replace('{botcolor}', '4b1218')       
    if '{guild.icon}' in params:
      if user.guild.icon:
        params=params.replace('{guild.icon}', user.guild.icon.url)
      else: 
        params=params.replace('{guild.icon}', "https://none.none")        

    return params

 async def to_object(params):

    x={}
    fields=[]
    content=None
    view=discord.ui.View()

    for part in EmbedBuilder.get_parts(params):
        
        if part.startswith('content:'):
            content=part[len('content:'):]

        if part.startswith('title:'):
            x['title']=part[len('title:'):]
        
        if part.startswith('description:'):
            x['description']=part[len('description:'):]

        if part.startswith('color:'):
            try:
                x['color']=int(part[len('color:'):].replace("#", ""), 16)
            except:
                x['color']=0x2f3136

        if part.startswith('image:'):
            x['image']={'url': part[len('image:'):]}

        if part.startswith('thumbnail:'):
            x['thumbnail']={'url': part[len('thumbnail:'):]}
        
        if part.startswith('author:'):
            z=part[len('author:'):].split(' && ')
            try:
                name=z[0] if z[0] else None
            except:
                name=None
            try:
                icon_url=z[1] if z[1] else None
            except:
                icon_url=None
            try:
                url=z[2] if z[2] else None
            except:
                url=None

            x['author']={'name': name}
            if icon_url:
                x['author']['icon_url']=icon_url
            if url:
                x['author']['url']=url

        if part.startswith('field:'):
            z=part[len('field:'):].split(' && ')
            try:
                name=z[0] if z[0] else None
            except:
                name=None
            try:
                value=z[1] if z[1] else None
            except:
                value=None
            try:
                inline=z[2] if z[2] else True
            except:
                inline=True

            if isinstance(inline, str):
                if inline == 'true':
                    inline=True

                elif inline == 'false':
                    inline=False

            fields.append({'name': name, 'value': value, 'inline': inline})

        if part.startswith('footer:'):
            z=part[len('footer:'):].split(' && ')
            try:
                text=z[0] if z[0] else None
            except:
                text=None
            try:
                icon_url=z[1] if z[1] else None
            except:
                icon_url=None
            x['footer']={'text': text}
            if icon_url:
                x['footer']['icon_url']=icon_url
                
        if part.startswith('button:'):
            z=part[len('button:'):].split(' && ')
            disabled=True
            style=discord.ButtonStyle.gray
            emoji=None 
            label=None 
            url=None
            for m in z:
             if "label:" in m: label=m.replace("label:", "")
             if "url:" in m: 
                url=m.replace("url:", "").strip()
                disabled=False
             if "emoji:" in m: emoji=m.replace("emoji:", "").strip()
             if "disabled" in m: disabled=True     
             if "style:" in m: 
               if m.replace("style:", "").strip() == "red": style=discord.ButtonStyle.red 
               elif m.replace("style:", "").strip() == "green": style=discord.ButtonStyle.green 
               elif m.replace("style:", "").strip() == "gray": style=discord.ButtonStyle.gray 
               elif m.replace("style:", "").strip() == "blue": style=discord.ButtonStyle.gray   

            view.add_item(discord.ui.Button(style=style, label=label, emoji=emoji, url=url, disabled=disabled))
            
    if not x: embed=None
    else:
        x['fields']=fields
        embed=discord.Embed.from_dict(x)
    return content, embed, view 

class EmbedScript(commands.Converter): 
  async def convert(self, ctx: commands.Context, argument: str):
   x = await EmbedBuilder.to_object(EmbedBuilder.embed_replacement(ctx.author, argument))
   if x[0] or x[1]: return {"content": x[0], "embed": x[1], "view": x[2]} 
   return {"content": EmbedBuilder.embed_replacement(ctx.author, argument)}

class GoToModal(discord.ui.Modal, title="Change Page Number"):
  page = discord.ui.TextInput(label="Page", placeholder="Page Number", max_length=3)

  async def on_submit(self, interaction: discord.Interaction) -> None:
   if int(self.page.value) > len(self.embeds): return await interaction.client.ext.send_warning(interaction, f"Please select a page **between** 1 and {len(self.embeds)}", ephemeral=True) 
   await interaction.response.edit_message(embed=self.embeds[int(self.page.value)-1]) 
  
  async def on_error(self, interaction: discord.Interaction, error: Exception) -> None: 
    await interaction.client.ext.send_warning(interaction, "Unable to **change**", ephemeral=True)

class PaginatorView(discord.ui.View): 
    def __init__(self, ctx: commands.Context, embeds: list): 
      super().__init__()  
      self.embeds = embeds
      self.ctx = ctx
      self.i = 0

    @discord.ui.button(emoji="<:left:1192774023009013832>", style=discord.ButtonStyle.gray)
    async def left(self, interaction: discord.Interaction, button: discord.ui.Button): 
      if interaction.user.id != self.ctx.author.id: return await interaction.client.ext.send_warning(interaction, "You're **not** the **author**")          
      if self.i == 0: 
        await interaction.response.edit_message(embed=self.embeds[-1])
        self.i = len(self.embeds)-1
        return
      self.i = self.i-1
      return await interaction.response.edit_message(embed=self.embeds[self.i])

    @discord.ui.button(emoji="<:right:1192773740879155220>", style=discord.ButtonStyle.gray)
    async def right(self, interaction: discord.Interaction, button: discord.ui.Button): 
      if interaction.user.id != self.ctx.author.id: return await interaction.client.ext.send_warning(interaction, "You're **not** the **author**")     
      if self.i == len(self.embeds)-1: 
        await interaction.response.edit_message(embed=self.embeds[0])
        self.i = 0
        return 
      self.i = self.i + 1  
      return await interaction.response.edit_message(embed=self.embeds[self.i])   
 
    @discord.ui.button(emoji="<:select:1192773742275866676>")
    async def goto(self, interaction: discord.Interaction, button: discord.ui.Button): 
     if interaction.user.id != self.ctx.author.id: return await interaction.client.ext.send_warning(interaction, "You're **not** the **author**")     
     modal = GoToModal()
     modal.embeds = self.embeds
     await interaction.response.send_modal(modal)
     await modal.wait()
     try:
      self.i = int(modal.page.value)-1
     except: pass 
    
    @discord.ui.button(emoji="<:close:1192773744586915923>", style=discord.ButtonStyle.gray)
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button): 
      if interaction.user.id != self.ctx.author.id: return await interaction.client.ext.send_warning(interaction, "You're **not** the **author**")     
      await interaction.message.delete()

    async def on_timeout(self) -> None: 
        mes = await self.message.channel.fetch_message(self.message.id)
        if mes is None: return
        if len(mes.components) == 0: return
        for item in self.children:
            item.disabled = True

        try: await self.message.edit(view=self)   
        except: pass


class StartUp:

 async def startup(bot):
    await bot.wait_until_ready()
    await bot.tree.sync()
    info_logger.info('Sucessfully synced applications commands')

 async def loadcogs(self): 
  for file in os.listdir("./events"): 
   if file.endswith(".py"):
    try:
     await self.load_extension(f"events.{file[:-3]}")
     info_logger.info(f"Loaded cog: {file[:-3]}".lower())
    except Exception as e: error_logger.error("Failed to load %s %s".lower(), file[:-3], e)
  for fil in os.listdir("./cogs"):
   if fil.endswith(".py"):
    try:
     await self.load_extension(f"cogs.{fil[:-3]}")
     info_logger.info(f"Loaded cog: {fil[:-3]}".lower())
    except Exception as e: error_logger.error("Failed to load: %s %s".lower(), fil[:-3], e)

 async def identify(self):
    payload = {
        'op': self.IDENTIFY,
        'd': {
            'token': self.token,
            'properties': {
                '$os': sys.platform,
                '$browser': 'Discord iOS',
                '$device': 'Discord iOS',
                '$referrer': '',
                '$referring_domain': ''
            },
            'compress': True,
            'large_threshold': 250,
            'v': 3
        }
    }

    if self.shard_id is not None and self.shard_count is not None:
        payload['d']['shard'] = [self.shard_id, self.shard_count]

    state = self._connection
    if state._activity is not None or state._status is not None:
        payload['d']['presence'] = {
            'status': state._status,
            'game': state._activity,
            'since': 0,
            'afk': False
        }

    if state._intents is not None:
        payload['d']['intents'] = state._intents.value

    await self.call_hooks('before_identify', self.shard_id, initial=self._initial_identify)
    await self.send_as_json(payload)

async def create_db(self: commands.AutoShardedBot): 
  await self.db.execute("CREATE TABLE IF NOT EXISTS prefixes (guild_id BIGINT, prefix TEXT)")  
  await self.db.execute("CREATE TABLE IF NOT EXISTS selfprefix (user_id BIGINT, prefix TEXT)") 
  await self.db.execute("CREATE TABLE IF NOT EXISTS nodata (user_id BIGINT, state TEXT)")       
  await self.db.execute("CREATE TABLE IF NOT EXISTS snipe (guild_id BIGINT, channel_id BIGINT, author TEXT, content TEXT, attachment TEXT, avatar TEXT, time TIMESTAMPTZ)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS afk (guild_id BIGINT, user_id BIGINT, reason TEXT, time INTEGER);")
  await self.db.execute("CREATE TABLE IF NOT EXISTS voicemaster (guild_id BIGINT, channel_id BIGINT, interface BIGINT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS vcs (user_id BIGINT, voice BIGINT)") 
  await self.db.execute("CREATE TABLE IF NOT EXISTS fake_permissions (guild_id BIGINT, role_id BIGINT, permissions TEXT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS confess (guild_id BIGINT, channel_id BIGINT, confession INTEGER);")
  await self.db.execute("CREATE TABLE IF NOT EXISTS authorize (guild_id BIGINT, buyer BIGINT, tags TEXT, transfers INTEGER, boosted TEXT)") 
  await self.db.execute("CREATE TABLE IF NOT EXISTS marry (author BIGINT, soulmate BIGINT, time INTEGER)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS mediaonly (guild_id BIGINT, channel_id BIGINT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS tickets (guild_id BIGINT, message TEXT, channel_id BIGINT, category BIGINT, color INTEGER, logs BIGINT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS opened_tickets (guild_id BIGINT, channel_id BIGINT, user_id BIGINT)") 
  await self.db.execute("CREATE TABLE IF NOT EXISTS ticket_topics (guild_id BIGINT, name TEXT, description TEXT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS pingonjoin (channel_id BIGINT, guild_id BIGINT);")
  await self.db.execute("CREATE TABLE IF NOT EXISTS autorole (role_id BIGINT, guild_id BIGINT);")
  await self.db.execute("CREATE TABLE IF NOT EXISTS levels (guild_id BIGINT, author_id BIGINT, exp INTEGER, level INTEGER, total_xp INTEGER)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS levelsetup (guild_id BIGINT, channel_id BIGINT, destination TEXT)") 
  await self.db.execute("CREATE TABLE IF NOT EXISTS levelroles (guild_id BIGINT, level INTEGER, role_id BIGINT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS oldusernames (username TEXT, discriminator TEXT, time INTEGER, user_id BIGINT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS donor (user_id BIGINT, time INTEGER);")
  await self.db.execute("CREATE TABLE IF NOT EXISTS restore (guild_id BIGINT, user_id BIGINT, roles TEXT);")
  await self.db.execute("CREATE TABLE IF NOT EXISTS lastfm (user_id BIGINT, username TEXT);")
  await self.db.execute("CREATE TABLE IF NOT EXISTS lastfmcc (user_id BIGINT, command TEXT);")
  await self.db.execute("CREATE TABLE IF NOT EXISTS lfmode (user_id BIGINT, mode TEXT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS lfcrowns (user_id BIGINT, artist TEXT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS lfreactions (user_id BIGINT, reactions TEXT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS starboardmes (guild_id BIGINT, channel_starboard_id BIGINT, channel_message_id BIGINT, message_starboard_id BIGINT, message_id BIGINT)") 
  await self.db.execute("CREATE TABLE IF NOT EXISTS starboard (guild_id BIGINT, channel_id BIGINT, count INTEGER, emoji_id BIGINT, emoji_text TEXT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS seen (guild_id BIGINT, user_id BIGINT, time INTEGER);")
  await self.db.execute("CREATE TABLE IF NOT EXISTS booster_module (guild_id BIGINT, base BIGINT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS booster_roles (guild_id BIGINT, user_id BIGINT, role_id BIGINT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS hardban (guild_id BIGINT, banned BIGINT, author BIGINT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS forcenick (guild_id BIGINT, user_id BIGINT, nickname TEXT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS uwulock (guild_id BIGINT, user_id BIGINT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS autopfp (guild_id BIGINT, channel_id BIGINT, genre TEXT, type TEXT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS antiinvite (guild_id BIGINT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS whitelist (guild_id BIGINT, module TEXT, object_id BIGINT, mode TEXT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS invoke (guild_id BIGINT, command TEXT, embed TEXT)") 
  await self.db.execute("CREATE TABLE IF NOT EXISTS chatfilter (guild_id BIGINT, word TEXT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS autoreact (guild_id BIGINT, trigger TEXT, emojis TEXT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS autoresponder (guild_id BIGINT, trigger TEXT, response TEXT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS welcome (guild_id BIGINT, channel_id BIGINT, mes TEXT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS leave (guild_id BIGINT, channel_id BIGINT, mes TEXT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS boost (guild_id BIGINT, channel_id BIGINT, mes TEXT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS antiraid (guild_id BIGINT, command TEXT, punishment TEXT, seconds INTEGER)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS disablecommand (guild_id BIGINT, command TEXT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS reactionrole (guild_id BIGINT, message_id BIGINT, channel_id BIGINT, role_id BIGINT, emoji_id BIGINT, emoji_text TEXT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS editsnipe (guild_id BIGINT, channel_id BIGINT, author_name TEXT, author_avatar TEXT, before_content TEXT, after_content TEXT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS reactionsnipe (guild_id BIGINT, channel_id BIGINT, author_name TEXT, author_avatar TEXT, emoji_name TEXT, emoji_url TEXT, message_id BIGINT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS mod (guild_id BIGINT, channel_id BIGINT, jail_id BIGINT, role_id BIGINT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS cases (guild_id BIGINT, count INTEGER)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS warns (guild_id BIGINT, user_id BIGINT, author_id BIGINT, time TEXT, reason TEXT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS jail (guild_id BIGINT, user_id BIGINT, roles TEXT)")
  await self.db.execute('CREATE TABLE IF NOT EXISTS cmderror (code TEXT, error TEXT)')
  await self.db.execute('CREATE TABLE IF NOT EXISTS joint (guild_id BIGINT, hits INTEGER, holder BIGINT)')
  await self.db.execute("CREATE TABLE IF NOT EXISTS counters (guild_id BIGINT, channel_type TEXT, channel_id BIGINT, channel_name TEXT, module TEXT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS bumps (guild_id BIGINT, bool TEXT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS boosterslost (guild_id BIGINT, user_id BIGINT, time INTEGER)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS dm (guild_id BIGINT, command TEXT, embed TEXT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS discrim (guild_id BIGINT, role_id BIGINT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS joindm (guild_id BIGINT, message TEXT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS birthday (user_id BIGINT, bday TIMESTAMPTZ, said TEXT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS antispam (guild_id BIGINT, seconds INTEGER, count INTEGER, punishment TEXT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS timezone (user_id BIGINT, zone TEXT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS webhook (guild_id BIGINT, channel_id BIGINT, code TEXT, url TEXT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS naughtycorner (guild_id BIGINT, channel_id BIGINT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS naughtycorner_members (guild_id BIGINT, user_id BIGINT)") 
  await self.db.execute("CREATE TABLE IF NOT EXISTS confess_members (guild_id BIGINT, user_id BIGINT, confession INTEGER)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS confess_mute (guild_id BIGINT, user_id BIGINT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS autotags (guild_id BIGINT, url TEXT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS antinuke_toggle (guild_id BIGINT, logs BIGINT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS antinuke (guild_id BIGINT, module TEXT, punishment TEXT, threshold INTEGER)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS giveaway (guild_id BIGINT, channel_id BIGINT, message_id BIGINT, winners INTEGER, members TEXT, finish TIMESTAMPTZ, host BIGINT, title TEXT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS gw_ended (channel_id BIGINT, message_id BIGINT, members TEXT)")
  await self.db.execute('CREATE TABLE IF NOT EXISTS diary (user_id BIGINT, text TEXT, title TEXT, date TEXT)')
  await self.db.execute("CREATE TABLE IF NOT EXISTS gamestats (user_id BIGINT PRIMARY KEY, game VARCHAR(255) NOT NULL, wins INT NOT NULL DEFAULT 0, loses INT NOT NULL DEFAULT 0, total INT NOT NULL DEFAULT 0)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS developerhardban (guild_id BIGINT, banned BIGINT, author BIGINT)")
  await self.db.execute("CREATE TABLE IF NOT EXISTS flags_scores (guild_id BIGINT NOT NULL, user_id BIGINT NOT NULL, points INT DEFAULT 0, PRIMARY KEY (guild_id, user_id));")
  await self.db.execute("CREATE TABLE IF NOT EXISTS btc_subscriptions (user_id BIGINT NOT NULL, transaction VARCHAR(255), PRIMARY KEY (user_id, transaction))")