import os
import discord
from discord.ext import commands
from keep_alive import keep_alive

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Dicionários globais para gerenciar as filas de cada modo
# Estrutura: filas[modo][subcategoria] = [lista de membros]
filas = {
    "1v1": {"Taxa R$ 0,30": []},
    "2v2": {"R$ 2,00": [], "R$ 4,00": []},
    "3v3": {"R$ 3,00": [], "R$ 6,00": []}
}

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

# --- VIEW DO PAINEL PRINCIPAL ---
class PainelCompletoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    # Botão do 1v1 (Taxa da sala R$ 0,30)
    @discord.ui.button(label="1v1 - Taxa R$ 0,30", style=discord.ButtonStyle.green, custom_id="1v1_taxa", emoji="🪙", row=0)
    async def f_1v1_taxa(self, interaction: discord.Interaction, button: discord.ui.Button):
        await entrar_na_fila(interaction, "1v1", "Taxa R$ 0,30", 2)

    # Botões do 2v2 (Valores: R$ 2,00 e R$ 4,00)
    @discord.ui.button(label="2v2 - R$ 2,00", style=discord.ButtonStyle.blurple, custom_id="2v2_2rs", emoji="💵", row=1)
    async def f_2v2_2rs(self, interaction: discord.Interaction, button: discord.ui.Button):
        await entrar_na_fila(interaction, "2v2", "R$ 2,00", 4)

    @discord.ui.button(label="2v2 - R$ 4,00", style=discord.ButtonStyle.blurple, custom_id="2v2_4rs", emoji="💵", row=1)
    async def f_2v2_4rs(self, interaction: discord.Interaction, button: discord.ui.Button):
        await entrar_na_fila(interaction, "2v2", "R$ 4,00", 4)

    # Botões do 3v3 (Valores: R$ 3,00 e R$ 6,00)
    @discord.ui.button(label="3v3 - R$ 3,00", style=discord.ButtonStyle.grey, custom_id="3v3_3rs", emoji="💵", row=2)
    async def f_3v3_3rs(self, interaction: discord.Interaction, button: discord.ui.Button):
        await entrar_na_fila(interaction, "3v3", "R$ 3,00", 6)

    @discord.ui.button(label="3v3 - R$ 6,00", style=discord.ButtonStyle.grey, custom_id="3v3_6rs", emoji="💵", row=2)
    async def f_3v3_6rs(self, interaction: discord.Interaction, button: discord.ui.Button):
        await entrar_na_fila(interaction, "3v3", "R$ 6,00", 6)

    # Botão de Ranking
    @discord.ui.button(label="Ver Ranking Geral", style=discord.ButtonStyle.secondary, custom_id="btn_ranking", emoji="🏆", row=3)
    async def ver_ranking(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🏆 **Ranking Geral:**\nNenhum jogador pontuou no ranking ainda.", ephemeral=True)

async def entrar_na_fila(interaction: discord.Interaction, modo: str, subcategoria: str, limite: int):
    user = interaction.user
    lista = filas[modo][subcategoria]

    if user in lista:
        await interaction.response.send_message("Você já está nessa fila!", ephemeral=True)
        return

    lista.append(user)
    
    if len(lista) < limite:
        nomes_esperando = ", ".join([m.mention for m in lista])
        await interaction.response.send_message(f"✅ Você entrou na fila **{modo} ({subcategoria})**!\n⏳ **Aguardando o oponente...** Jogadores na fila: {nomes_esperando}", ephemeral=True)
    else:
        jogadores_partida = lista[:limite]
        filas[modo][subcategoria] = [] # Limpa a fila

        await interaction.response.send_message(f"🚀 Fila completa para **{modo} ({subcategoria})**! Criando canal privado...", ephemeral=True)
        await criar_canal_partida(interaction.guild, modo, subcategoria, jogadores_partida)

async def criar_canal_partida(guild: discord.Guild, modo: str, subcategoria: str, jogadores: list):
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    
    for jogador in jogadores:
        overwrites[jogador] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    canal = await guild.create_text_channel(name=f"⚔️-{modo}-{subcategoria}".replace("$", "").replace(",", "").replace(" ", "-").lower(), overwrites=overwrites)

    mencoes = ", ".join([j.mention for j in jogadores])
    
    view = ConfirmarPartidaView(jogadores, canal)
    embed = discord.Embed(
        title=f"Partida de {modo} | {subcategoria}",
        description=f"Jogadores: {mencoes}\n\n**Combinem suas regras, o valor da aposta e confirme a partida abaixo!**",
        color=0xff0000
    )
    await canal.send(content=mencoes, embed=embed, view=view)

# --- VIEW DE CONFIRMAÇÃO DE PARTIDA ---
class ConfirmarPartidaView(discord.ui.View):
    def __init__(self, jogadores, canal):
        super().__init__(timeout=None)
        self.jogadores = jogadores
        self.canal = canal
        self.confirmados = set()

    @discord.ui.button(label="Confirmar Partida", style=discord.ButtonStyle.green, emoji="✅")
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.jogadores:
            await interaction.response.send_message("Você não faz parte desta partida!", ephemeral=True)
            return

        self.confirmados.add(interaction.user)
        restantes = len(self.jogadores) - len(self.confirmados)

        if restantes > 0:
            await interaction.response.send_message(f"✅ {interaction.user.mention} confirmou! Faltam **{restantes}** confirmações.", ephemeral=False)
        else:
            await interaction.response.send_message("🎉 **Todas as confirmações realizadas!** Gerando sala...", ephemeral=False)
            
            for child in self.children:
                child.disabled = True
            await interaction.message.edit(view=self)

            await self.canal.send(".cs")

            view_vencedor = DefinirVencedorView(self.jogadores, self.canal)
            await self.canal.send("🏆 **A partida foi iniciada!** Assim que terminar, defina o vencedor abaixo:", view=view_vencedor)

# --- VIEW DE DEFINIR VENCEDOR ---
class DefinirVencedorView(discord.ui.View):
    def __init__(self, jogadores, canal):
        super().__init__(timeout=None)
        self.jogadores = jogadores
        self.canal = canal

        for i, jogador in enumerate(jogadores):
            self.add_item(VencedorButton(jogador, label=f"Vencedor: {jogador.display_name}", row=i//2))

class VencedorButton(discord.ui.Button):
    def __init__(self, vencedor, label, row):
        super().__init__(style=discord.ButtonStyle.primary, label=label, row=row)
        self.vencedor = vencedor

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"🏆 **Vitória contabilizada para {self.vencedor.mention}!** Parabéns!\nEste canal será fechado em instantes.", ephemeral=False)
        
        for child in self.view.children:
            child.disabled = True
        await interaction.message.edit(view=self)

@bot.command(name="painel")
async def painel(ctx):
    embed = discord.Embed(
        title="🏆 PAINEL DE RANKING GERAL 🏆",
        description="1º 🥇 *Nenhum registrado*\n2º 🥈 *Nenhum registrado*\n3º 🥉 *Nenhum registrado*\n\n---------------------------------------------\n⚔️ **ESCOLHA SUA FILA ABAIXO:**",
        color=0xffd700
    )
    embed.set_thumbnail(url="https://i.imgur.com/4M34hi2.png")
    
    view = PainelCompletoView()
    await ctx.send(embed=embed, view=view)

keep_alive()

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("ERRO: DISCORD_TOKEN não encontrado nas variáveis de ambiente!")
