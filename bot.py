import os
import discord
from discord.ext import commands
from keep_alive import keep_alive

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

# --- MODAIS E VIEWS DE ESCOLHA DE GELO ---
class GeloView(discord.ui.View):
    def __init__(self, mode_name, price):
        super().__init__(timeout=None)
        self.mode_name = mode_name
        self.price = price

    @discord.ui.button(label="Gelo Normal", style=discord.ButtonStyle.secondary, emoji="🧊")
    async def gelo_normal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.enviar_fila(interaction, "Gelo Normal")

    @discord.ui.button(label="Gelo Infinito", style=discord.ButtonStyle.secondary, emoji="🧊")
    async def gelo_infinito(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.enviar_fila(interaction, "Gelo Infinito")

    @discord.ui.button(label="Sair", style=discord.ButtonStyle.danger, emoji="✖️")
    async def sair(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Você saiu da fila.", ephemeral=True)

    async def enviar_fila(self, interaction: discord.Interaction, tipo_gelo: str):
        embed = discord.Embed(title=f"{self.mode_name} | R$ {self.price}", color=0xff0000)
        embed.add_field(name="Jogadores", value=f"{interaction.user.mention} | {tipo_gelo}", inline=False)
        
        # Thumbnail opcional baseada no seu print
        embed.set_thumbnail(url="https://i.imgur.com/4M34hi2.png") # substitua se quiser
        
        view_sair = SairFilaView()
        await interaction.response.send_message(embed=embed, view=view_sair)

class SairFilaView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Sair", style=discord.ButtonStyle.danger, emoji="✖️")
    async def sair(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()
        await interaction.response.send_message("Você saiu da fila com sucesso!", ephemeral=True)

# --- PAINEL PRINCIPAL DE FILAS ---
class PainelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Entrar na Fila 1v1", style=discord.ButtonStyle.green, custom_id="btn_1v1", emoji="📌")
    async def fila_1v1(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = GeloView("1x1 Mobile", "2,00")
        await interaction.response.send_message("Escolha o tipo de gelo para o **1v1**:", view=view, ephemeral=True)

    @discord.ui.button(label="Entrar na Fila 2v2", style=discord.ButtonStyle.green, custom_id="btn_2v2", emoji="📌")
    async def fila_2v2(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = GeloView("2x2 Mobile", "4,00")
        await interaction.response.send_message("Escolha o tipo de gelo para o **2v2**:", view=view, ephemeral=True)

    @discord.ui.button(label="Entrar na Fila 3v3", style=discord.ButtonStyle.green, custom_id="btn_3v3", emoji="📌")
    async def fila_3v3(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = GeloView("3x3 Mobile", "6,00")
        await interaction.response.send_message("Escolha o tipo de gelo para o **3v3**:", view=view, ephemeral=True)

class RankingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ver Ranking Geral", style=discord.ButtonStyle.primary, custom_id="btn_ranking", emoji="🏆")
    async def ranking(self, interaction: discord.Interaction):
        await interaction.response.send_message("🏆 **Ranking Geral:**\nNenhum jogador pontuou ainda.", ephemeral=True)

@bot.command(name="painel")
async def painel(ctx):
    embed = discord.Embed(title="⚔️ Painel de Filas 1v1, 2v2 e 3v3", description="Clique no botão abaixo para entrar na fila do modo desejado:", color=0x2b2d31)
    
    view = discord.ui.View()
    # Adicionando os botões organizados no painel
    view.add_item(discord.ui.Button(label="Entrar na Fila", style=discord.ButtonStyle.green, custom_id="btn_1v1", emoji="📌"))
    
    # Mandando o painel completo
    await ctx.send(embed=embed, view=PainelView())

# Mantém o bot online com o flask rodando em segundo plano
keep_alive()

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("ERRO: DISCORD_TOKEN não encontrado nas variáveis de ambiente!")
