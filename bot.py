import discord
from discord.ext import commands
from discord.ui import View, Button
import sqlite3
import asyncio
import os
from keep_alive import keep_alive

# Configuração de Intents do Discord
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ==================== BANCO DE DADOS ====================
def init_db():
    conn = sqlite3.connect("ranking.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ranking (
            user_id INTEGER PRIMARY KEY,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def add_win(user_id):
    conn = sqlite3.connect("ranking.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO ranking (user_id, wins, losses) VALUES (?, 0, 0)", (user_id,))
    cursor.execute("UPDATE ranking SET wins = wins + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def add_loss(user_id):
    conn = sqlite3.connect("ranking.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO ranking (user_id, wins, losses) VALUES (?, 0, 0)", (user_id,))
    cursor.execute("UPDATE ranking SET wins = wins + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_top_players():
    conn = sqlite3.connect("ranking.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, wins FROM ranking ORDER BY wins DESC LIMIT 10")
    data = cursor.fetchall()
    conn.close()
    return data

# ==================== FILAS E VIEWS ====================

filas = {
    "1v1": [],
    "2v2": [],
    "3v3": []
}

class MatchControlView(View):
    def __init__(self, team1, team2, mode, category, channel_to_delete):
        super().__init__(timeout=None)
        self.team1 = team1
        self.team2 = team2
        self.mode = mode
        self.category = category
        self.channel_to_delete = channel_to_delete
        self.ready_players = set()

    @discord.ui.button(label="Pronto / Aceitar AP", style=discord.ButtonStyle.green, custom_id="btn_pronto")
    async def pronto_callback(self, interaction: discord.Interaction, button: Button):
        all_players = self.team1 + self.team2
        if interaction.user not in all_players:
            await interaction.response.send_message("Você não faz parte desta partida!", ephemeral=True)
            return

        self.ready_players.add(interaction.user)
        
        if len(self.ready_players) == len(all_players):
            button.disabled = True
            await interaction.response.edit_message(content="🔥 **Todos prontos! Partida iniciada.**", view=self)
            await interaction.channel.send(".cs")
        else:
            await interaction.response.send_message(f"Você marcou presença! ({len(self.ready_players)}/{len(all_players)})", ephemeral=True)

    @discord.ui.button(label="Registrar Vitória Equipe 1", style=discord.ButtonStyle.blurple, custom_id="btn_win1")
    async def win1_callback(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Apenas administradores podem registrar o resultado.", ephemeral=True)
            return
        
        for p in self.team1:
            add_win(p.id)
        for p in self.team2:
            add_loss(p.id)

        winners_mention = " e ".join([p.mention for p in self.team1])
        await interaction.response.send_message(f"🏆 **Resultado computado!** Vitória da equipe de {winners_mention}.")
        await self.cleanup_match()

    @discord.ui.button(label="Registrar Vitória Equipe 2", style=discord.ButtonStyle.blurple, custom_id="btn_win2")
    async def win2_callback(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Apenas administradores podem registrar o resultado.", ephemeral=True)
            return
        
        for p in self.team2:
            add_win(p.id)
        for p in self.team1:
            add_loss(p.id)

        winners_mention = " e ".join([p.mention for p in self.team2])
        await interaction.response.send_message(f"🏆 **Resultado computado!** Vitória da equipe de {winners_mention}.")
        await self.cleanup_match()

    async def cleanup_match(self):
        await asyncio.sleep(5)
        for c in self.category.channels:
            await c.delete()
        await self.category.delete()


class QueueView(View):
    def __init__(self, mode):
        super().__init__(timeout=None)
        self.mode = mode

    @discord.ui.button(label="Entrar na Fila", style=discord.ButtonStyle.green, custom_id="btn_entrar_fila")
    async def entrar_fila(self, interaction: discord.Interaction, button: Button):
        user = interaction.user
        mode = self.mode
        
        team_size = 1 if mode == "1v1" else (2 if mode == "2v2" else 3)
        required_players = team_size * 2

        if user in filas[mode]:
            filas[mode].remove(user)
            await interaction.response.send_message("❌ Você saiu da fila.", ephemeral=True)
        else:
            filas[mode].append(user)
            await interaction.response.send_message(f"✅ Você entrou na fila **{mode}**! ({len(filas[mode])}/{required_players})", ephemeral=True)

        if len(filas[mode]) >= required_players:
            players_matched = [filas[mode].pop(0) for _ in range(required_players)]
            team1 = players_matched[:team_size]
            team2 = players_matched[team_size:]
            
            guild = interaction.guild
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                guild.me: discord.PermissionOverwrite(view_channel=True)
            }
            for p in team1 + team2:
                overwrites[p] = discord.PermissionOverwrite(view_channel=True, send_messages=True, connect=True)

            category = await guild.create_category(f"⚔️ {mode} - Partida")
            text_channel = await guild.create_text_channel(f"partida-{mode}-{user.name}", category=category, overwrites=overwrites)
            voice_channel = await guild.create_voice_channel(f"🔊 Call {mode}", category=category, overwrites=overwrites)

            team1_str = " & ".join([p.mention for p in team1])
            team2_str = " & ".join([p.mention for p in team2])

            view = MatchControlView(team1, team2, mode, category, text_channel)
            await text_channel.send(
                f"🎮 **Partida Formada!**\nEquipe 1: {team1_str}\nEquipe 2: {team2_str}\n\n"
                f"Entrem na call {voice_channel.mention} com um administrador para acertar as regras.\n"
                f"Apertem o botão abaixo quando estiverem prontos!",
                view=view
            )


class RankingView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ver Ranking Geral", style=discord.ButtonStyle.blurple, custom_id="btn_ver_ranking")
    async def ver_ranking(self, interaction: discord.Interaction, button: Button):
        top_players = get_top_players()
        if not top_players:
            await interaction.response.send_message("Ainda não há registros no ranking.", ephemeral=True)
            return
        
        desc = ""
        for i, (uid, wins) in enumerate(top_players, start=1):
            member = interaction.guild.get_member(uid)
            name = member.name if member else f"Usuário ID: {uid}"
            medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else f"{i}º"))
            desc += f"{medal} **{name}** — `{wins}` vitórias\n"

        embed = discord.Embed(title="🏆 Ranking de Vitórias do Servidor", description=desc, color=discord.Color.gold())
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ==================== COMANDOS DO BOT ====================

@bot.event
async def on_ready():
    init_db()
    bot.add_view(QueueView("1v1"))
    bot.add_view(QueueView("2v2"))
    bot.add_view(QueueView("3v3"))
    bot.add_view(RankingView())
    print(f"Bot conectado como {bot.user}!")

@bot.command()
@commands.has_permissions(administrator=True)
async def painel(ctx):
    await ctx.send("### ⚔️ Painel de Filas 1v1, 2v2 e 3v3\nClique no botão abaixo para entrar na fila do modo desejado:")
    await ctx.send("📌 **Fila 1v1**", view=QueueView("1v1"))
    await ctx.send("📌 **Fila 2v2**", view=QueueView("2v2"))
    await ctx.send("📌 **Fila 3v3**", view=QueueView("3v3"))
    
    await ctx.send("\n### 🏆 Painel de Ranking\nClique para consultar os melhores jogadores:", view=RankingView())

keep_alive()

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)

