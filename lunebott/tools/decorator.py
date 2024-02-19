import discord, datetime, humanize
from discord.ext import commands

def is_reskin():
 async def predicate(ctx: commands.Context): 
  check = await ctx.bot.db.fetchrow("SELECT * FROM reskin_toggle WHERE guild_id = $1", ctx.guild.id)
  if not check: await ctx.warn("Reskin is **not** enabled")
  return check is not None 
 return commands.check(predicate)